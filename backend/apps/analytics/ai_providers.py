"""
AI Provider Manager with Automatic Failover and Cost Optimization.

Provides a unified interface for multiple AI providers (Claude, OpenAI)
with automatic failover when the primary provider fails.

Features:
- Multi-provider support with automatic failover
- Anthropic prompt caching for 90% cost reduction on repeated context
- Tiered model selection (Haiku/Sonnet/Opus) based on query complexity
- Request logging for cost monitoring

Usage:
    manager = AIProviderManager(
        primary_provider='anthropic',
        api_keys={'anthropic': 'sk-...', 'openai': 'sk-...'},
        fallback_order=['anthropic', 'openai']
    )
    result = manager.enhance_insights(insights, context)
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Callable

logger = logging.getLogger(__name__)


PROCUREMENT_SYSTEM_PROMPT = """You are an expert procurement analytics advisor. Your role is to analyze
spending data, identify cost optimization opportunities, assess supplier risks, and provide
actionable recommendations.

CORE EXPERTISE:
- Spend analysis and category management
- Supplier relationship management and risk assessment
- Contract optimization and compliance
- Procurement process efficiency
- Strategic sourcing and consolidation opportunities

RESPONSE GUIDELINES:
1. Be specific and actionable - provide concrete steps, not vague suggestions
2. Quantify impact whenever possible - use dollar amounts and percentages
3. Prioritize by business value - focus on high-impact, achievable actions
4. Consider implementation effort and timeline
5. Flag risks and dependencies clearly

OUTPUT REQUIREMENTS:
- Use the provided tool/function schema to structure your response
- Ensure all monetary values are realistic based on the provided data
- Never fabricate supplier names, categories, or metrics not in the source data
- Express confidence levels as decimals (0.0 to 1.0)

CRITICAL CONSTRAINTS (MANDATORY):
1. NEVER state monetary values without citing source data
2. NEVER extrapolate trends beyond the provided date range
3. NEVER reference suppliers or categories not in the provided data
4. NEVER claim savings that exceed total spend for the relevant scope
5. ALWAYS flag uncertainty with confidence scores (0.0-1.0)
6. ALWAYS validate that percentages sum correctly when applicable

REQUIRED CITATIONS:
- Spending claims must reference specific data points from the provided context
- Supplier counts must match the exact data provided
- Date ranges must stay within the bounds of the provided transaction data
- Savings estimates must be justifiable from the source spending data

WHEN UNCERTAIN:
- State "Based on available data, [claim] (confidence: X.X)"
- Lower confidence scores for inferences vs. direct data observations
- Explicitly note when additional data would improve the recommendation"""


@dataclass
class LLMRequestMetrics:
    """Metrics from an LLM API call for logging and cost tracking."""
    provider: str
    model: str
    model_tier: str
    request_type: str
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: int = 0
    prompt_cache_read_tokens: int = 0
    prompt_cache_write_tokens: int = 0
    error: Optional[str] = None

    @property
    def cost_usd(self) -> Decimal:
        """Calculate cost based on model pricing."""
        pricing = {
            'claude-sonnet-4-20250514': {'input': 3.0, 'output': 15.0, 'cache_read': 0.30},
            'claude-3-5-haiku-20241022': {'input': 0.25, 'output': 1.25, 'cache_read': 0.025},
            'claude-opus-4-20250514': {'input': 15.0, 'output': 75.0, 'cache_read': 1.50},
            'gpt-4-turbo-preview': {'input': 10.0, 'output': 30.0, 'cache_read': 0},
            'gpt-4o-mini': {'input': 0.15, 'output': 0.60, 'cache_read': 0},
        }
        model_pricing = pricing.get(self.model, {'input': 3.0, 'output': 15.0, 'cache_read': 0.30})

        regular_input_tokens = self.tokens_input - self.prompt_cache_read_tokens
        input_cost = (regular_input_tokens / 1_000_000) * model_pricing['input']
        cache_cost = (self.prompt_cache_read_tokens / 1_000_000) * model_pricing['cache_read']
        output_cost = (self.tokens_output / 1_000_000) * model_pricing['output']

        return Decimal(str(round(input_cost + cache_cost + output_cost, 6)))


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    name: str = "base"

    @abstractmethod
    def enhance_insights(
        self,
        insights: list,
        context: dict,
        tool_schema: dict
    ) -> Optional[dict]:
        """
        Generate insight enhancements using the provider's API.

        Args:
            insights: List of insight dictionaries
            context: Comprehensive context for AI analysis
            tool_schema: Tool/function schema for structured output

        Returns:
            Structured enhancement dict or None on failure
        """
        pass

    @abstractmethod
    def analyze_single_insight(
        self,
        insight: dict,
        tool_schema: dict
    ) -> Optional[dict]:
        """
        Analyze a single insight (cost-efficient model).

        Args:
            insight: Single insight dictionary
            tool_schema: Tool/function schema for structured output

        Returns:
            Analysis dict or None on failure
        """
        pass

    @abstractmethod
    def deep_analysis(
        self,
        insight_data: dict,
        context: dict,
        tool_schema: dict
    ) -> Optional[dict]:
        """
        Perform comprehensive deep analysis on an insight.

        Args:
            insight_data: Insight to analyze
            context: Organization/spending context
            tool_schema: Tool/function schema for structured output

        Returns:
            Deep analysis dict or None on failure
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available and configured."""
        pass

    @abstractmethod
    def health_check(self) -> dict:
        """
        Perform a health check on the provider.

        Returns:
            Dict with 'healthy' (bool), 'latency_ms' (int), 'error' (str or None)
        """
        pass


class AnthropicProvider(AIProvider):
    """
    Claude API provider implementation with prompt caching.

    Features:
    - Prompt caching for 90% cost reduction on repeated system prompts
    - Tiered model selection support
    - Metrics collection for cost tracking
    """

    name = "anthropic"

    MODELS = {
        'haiku': 'claude-3-5-haiku-20241022',
        'sonnet': 'claude-sonnet-4-20250514',
        'opus': 'claude-opus-4-20250514',
    }

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None
        self._last_metrics: Optional[LLMRequestMetrics] = None

    @property
    def client(self):
        if not self._client and self.api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                logger.warning("anthropic package not installed")
        return self._client

    @property
    def last_metrics(self) -> Optional[LLMRequestMetrics]:
        return self._last_metrics

    def is_available(self) -> bool:
        return bool(self.api_key and self.client)

    def health_check(self) -> dict:
        if not self.is_available():
            return {"healthy": False, "latency_ms": 0, "error": "Not configured"}

        start = time.time()
        try:
            self.client.messages.create(
                model=self.MODELS['haiku'],
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}]
            )
            latency = int((time.time() - start) * 1000)
            return {"healthy": True, "latency_ms": latency, "error": None}
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return {"healthy": False, "latency_ms": latency, "error": str(e)}

    def _build_cacheable_system_prompt(self, context: Optional[dict] = None) -> list:
        """
        Build system prompt with cache_control for Anthropic prompt caching.

        The system prompt is marked as ephemeral (5-minute cache) to enable
        90% cost reduction on repeated calls with the same context.
        """
        blocks = [
            {
                "type": "text",
                "text": PROCUREMENT_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"}
            }
        ]

        if context and context.get('organization'):
            org_context = f"""
ORGANIZATION CONTEXT:
- Name: {context['organization'].get('name', 'Unknown')}
- Procurement Maturity: {context['organization'].get('procurement_maturity', 'developing')}

SPENDING CONTEXT:
- Total YTD Spend: ${context.get('spending', {}).get('total_ytd', 0):,.2f}
- Supplier Count: {context.get('spending', {}).get('supplier_count', 0)}
- Category Count: {context.get('spending', {}).get('category_count', 0)}
- Transaction Count: {context.get('spending', {}).get('transaction_count', 0)}

TOP CATEGORIES:
{json.dumps(context.get('top_categories', [])[:5], indent=2)}

TOP SUPPLIERS:
{json.dumps(context.get('top_suppliers', [])[:5], indent=2)}"""

            blocks.append({
                "type": "text",
                "text": org_context,
                "cache_control": {"type": "ephemeral"}
            })

        return blocks

    def _extract_metrics(
        self,
        response,
        model: str,
        request_type: str,
        start_time: float
    ) -> LLMRequestMetrics:
        """Extract metrics from Anthropic API response including cache usage."""
        model_tier = 'sonnet'
        if 'haiku' in model:
            model_tier = 'haiku'
        elif 'opus' in model:
            model_tier = 'opus'

        metrics = LLMRequestMetrics(
            provider='anthropic',
            model=model,
            model_tier=model_tier,
            request_type=request_type,
            tokens_input=response.usage.input_tokens,
            tokens_output=response.usage.output_tokens,
            latency_ms=int((time.time() - start_time) * 1000),
            prompt_cache_read_tokens=getattr(response.usage, 'cache_read_input_tokens', 0) or 0,
            prompt_cache_write_tokens=getattr(response.usage, 'cache_creation_input_tokens', 0) or 0,
        )

        self._last_metrics = metrics
        return metrics

    def enhance_insights(
        self,
        insights: list,
        context: dict,
        tool_schema: dict,
        model: str = None
    ) -> Optional[dict]:
        if not self.is_available():
            return None

        model = model or self.MODELS['sonnet']
        start_time = time.time()

        try:
            system_blocks = self._build_cacheable_system_prompt(context)

            user_content = f"""Analyze these procurement insights and provide structured recommendations.

Current Insights ({len(insights)} total):
{json.dumps(context.get('insights', insights[:15]), indent=2)}

Provide actionable recommendations prioritized by impact and effort.
Focus on quick wins and high-impact actions that address the identified issues."""

            message = self.client.messages.create(
                model=model,
                max_tokens=2048,
                system=system_blocks,
                tools=[tool_schema],
                tool_choice={"type": "tool", "name": tool_schema["name"]},
                messages=[{"role": "user", "content": user_content}]
            )

            metrics = self._extract_metrics(message, model, 'enhance', start_time)
            logger.info(
                f"Anthropic enhance: {metrics.tokens_input} in, {metrics.tokens_output} out, "
                f"cache read: {metrics.prompt_cache_read_tokens}, cost: ${metrics.cost_usd}"
            )

            for block in message.content:
                if block.type == "tool_use" and block.name == tool_schema["name"]:
                    result = block.input
                    result['provider'] = 'anthropic'
                    result['model'] = model
                    result['generated_at'] = datetime.now().isoformat()
                    result['_metrics'] = {
                        'tokens_input': metrics.tokens_input,
                        'tokens_output': metrics.tokens_output,
                        'cache_read_tokens': metrics.prompt_cache_read_tokens,
                        'cost_usd': float(metrics.cost_usd),
                        'latency_ms': metrics.latency_ms,
                    }
                    return result

            logger.warning("Claude did not return tool_use response")
            return None

        except Exception as e:
            self._last_metrics = LLMRequestMetrics(
                provider='anthropic',
                model=model,
                model_tier='sonnet',
                request_type='enhance',
                latency_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )
            logger.error(f"Anthropic enhancement failed: {e}")
            raise

    def analyze_single_insight(
        self,
        insight: dict,
        tool_schema: dict,
        model: str = None
    ) -> Optional[dict]:
        if not self.is_available():
            return None

        model = model or self.MODELS['haiku']
        start_time = time.time()

        try:
            system_blocks = [
                {
                    "type": "text",
                    "text": PROCUREMENT_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"}
                }
            ]

            user_content = self._build_single_insight_prompt(insight)

            message = self.client.messages.create(
                model=model,
                max_tokens=500,
                system=system_blocks,
                tools=[tool_schema],
                tool_choice={"type": "tool", "name": tool_schema["name"]},
                messages=[{"role": "user", "content": user_content}]
            )

            metrics = self._extract_metrics(message, model, 'single_insight', start_time)

            for block in message.content:
                if block.type == "tool_use" and block.name == tool_schema["name"]:
                    result = block.input
                    result['provider'] = 'anthropic'
                    result['model'] = model
                    result['generated_at'] = datetime.now().isoformat()
                    result['_metrics'] = {
                        'tokens_input': metrics.tokens_input,
                        'tokens_output': metrics.tokens_output,
                        'cache_read_tokens': metrics.prompt_cache_read_tokens,
                        'cost_usd': float(metrics.cost_usd),
                        'latency_ms': metrics.latency_ms,
                    }
                    return result

            return None

        except Exception as e:
            self._last_metrics = LLMRequestMetrics(
                provider='anthropic',
                model=model,
                model_tier='haiku',
                request_type='single_insight',
                latency_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )
            logger.error(f"Anthropic single insight analysis failed: {e}")
            raise

    def deep_analysis(
        self,
        insight_data: dict,
        context: dict,
        tool_schema: dict,
        model: str = None
    ) -> Optional[dict]:
        if not self.is_available():
            return None

        model = model or self.MODELS['sonnet']
        start_time = time.time()

        try:
            system_blocks = self._build_cacheable_system_prompt(context)

            user_content = self._build_deep_analysis_prompt(insight_data)

            message = self.client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_blocks,
                tools=[tool_schema],
                tool_choice={"type": "tool", "name": tool_schema["name"]},
                messages=[{"role": "user", "content": user_content}]
            )

            metrics = self._extract_metrics(message, model, 'deep_analysis', start_time)
            logger.info(
                f"Anthropic deep_analysis: {metrics.tokens_input} in, {metrics.tokens_output} out, "
                f"cache read: {metrics.prompt_cache_read_tokens}, cost: ${metrics.cost_usd}"
            )

            for block in message.content:
                if block.type == "tool_use" and block.name == tool_schema["name"]:
                    result = block.input
                    result['insight_id'] = insight_data.get('id')
                    result['provider'] = 'anthropic'
                    result['model'] = model
                    result['generated_at'] = datetime.now().isoformat()
                    result['_metrics'] = {
                        'tokens_input': metrics.tokens_input,
                        'tokens_output': metrics.tokens_output,
                        'cache_read_tokens': metrics.prompt_cache_read_tokens,
                        'cost_usd': float(metrics.cost_usd),
                        'latency_ms': metrics.latency_ms,
                    }
                    return result

            return None

        except Exception as e:
            self._last_metrics = LLMRequestMetrics(
                provider='anthropic',
                model=model,
                model_tier='sonnet',
                request_type='deep_analysis',
                latency_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )
            logger.error(f"Anthropic deep analysis failed: {e}")
            raise

    def classify_query_complexity(self, query: str) -> str:
        """
        Use Haiku to classify query complexity for tiered model selection.

        Returns: 'simple', 'standard', or 'complex'
        """
        if not self.is_available():
            return 'standard'

        try:
            message = self.client.messages.create(
                model=self.MODELS['haiku'],
                max_tokens=20,
                messages=[{
                    "role": "user",
                    "content": f"""Classify this procurement query complexity. Reply with exactly one word: simple, standard, or complex.

Query: {query[:500]}

Classification:"""
                }]
            )

            response_text = message.content[0].text.strip().lower()
            if response_text in ['simple', 'standard', 'complex']:
                return response_text
            return 'standard'

        except Exception as e:
            logger.warning(f"Query classification failed: {e}")
            return 'standard'

    def select_model_for_task(self, task_type: str, complexity: str = None) -> str:
        """
        Select appropriate model based on task type and complexity.

        Args:
            task_type: 'enhance', 'single_insight', 'deep_analysis', 'classify', 'chat'
            complexity: Optional override - 'simple', 'standard', 'complex'

        Returns:
            Model identifier string
        """
        if task_type == 'classify':
            return self.MODELS['haiku']

        if task_type == 'single_insight':
            return self.MODELS['haiku']

        if complexity == 'simple':
            return self.MODELS['haiku']
        elif complexity == 'complex':
            return self.MODELS['opus']

        return self.MODELS['sonnet']

    def _build_single_insight_prompt(self, insight: dict) -> str:
        return f"""Analyze this procurement insight and provide detailed analysis:

Type: {insight['type']}
Title: {insight['title']}
Description: {insight['description']}
Severity: {insight['severity']}
Potential Savings: ${insight.get('potential_savings', 0):,.2f}
Confidence: {insight.get('confidence', 0) * 100:.0f}%

Additional Details:
{json.dumps(insight.get('details', {}), indent=2)}

Provide root cause analysis, industry benchmarks, and actionable remediation steps."""

    def _build_deep_analysis_prompt(self, insight_data: dict) -> str:
        return f"""Perform a comprehensive deep analysis of this procurement insight.

INSIGHT DETAILS:
- ID: {insight_data.get('id', 'N/A')}
- Type: {insight_data.get('type', 'N/A')}
- Title: {insight_data.get('title', 'N/A')}
- Description: {insight_data.get('description', 'N/A')}
- Severity: {insight_data.get('severity', 'N/A')}
- Confidence: {insight_data.get('confidence', 0) * 100:.0f}%
- Potential Savings: ${insight_data.get('potential_savings', 0):,.2f}

ADDITIONAL DETAILS:
{json.dumps(insight_data.get('details', {}), indent=2)}

RECOMMENDED ACTIONS (from initial analysis):
{json.dumps(insight_data.get('recommended_actions', []), indent=2)}

Provide a thorough analysis including:
1. Root cause analysis - identify the primary cause and contributing factors
2. Implementation roadmap - phased approach with specific tasks
3. Financial impact - detailed savings breakdown and ROI calculation
4. Risk factors - potential risks and mitigation strategies
5. Success metrics - KPIs to track implementation success
6. Stakeholder mapping - who needs to be involved
7. Industry context - benchmarks and best practices
8. Clear next steps - immediate actions to take"""


class OpenAIProvider(AIProvider):
    """
    OpenAI GPT API provider implementation with metrics tracking.

    Features:
    - Metrics collection for cost tracking
    - Model tier support (gpt-4o-mini, gpt-4-turbo)
    """

    name = "openai"

    MODELS = {
        'mini': 'gpt-4o-mini',
        'turbo': 'gpt-4-turbo-preview',
    }

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None
        self._last_metrics: Optional[LLMRequestMetrics] = None

    @property
    def client(self):
        if not self._client and self.api_key:
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                logger.warning("openai package not installed")
        return self._client

    @property
    def last_metrics(self) -> Optional[LLMRequestMetrics]:
        return self._last_metrics

    def is_available(self) -> bool:
        return bool(self.api_key and self.client)

    def health_check(self) -> dict:
        if not self.is_available():
            return {"healthy": False, "latency_ms": 0, "error": "Not configured"}

        start = time.time()
        try:
            self.client.chat.completions.create(
                model=self.MODELS['mini'],
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5
            )
            latency = int((time.time() - start) * 1000)
            return {"healthy": True, "latency_ms": latency, "error": None}
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return {"healthy": False, "latency_ms": latency, "error": str(e)}

    def _convert_to_openai_tool(self, tool_schema: dict) -> dict:
        """Convert Anthropic tool schema to OpenAI format."""
        return {
            "type": "function",
            "function": {
                "name": tool_schema["name"],
                "description": tool_schema["description"],
                "parameters": tool_schema["input_schema"]
            }
        }

    def _extract_metrics(
        self,
        response,
        model: str,
        request_type: str,
        start_time: float
    ) -> LLMRequestMetrics:
        """Extract metrics from OpenAI API response."""
        model_tier = 'gpt4_turbo' if 'turbo' in model else 'gpt4o_mini'

        metrics = LLMRequestMetrics(
            provider='openai',
            model=model,
            model_tier=model_tier,
            request_type=request_type,
            tokens_input=response.usage.prompt_tokens if response.usage else 0,
            tokens_output=response.usage.completion_tokens if response.usage else 0,
            latency_ms=int((time.time() - start_time) * 1000),
        )

        self._last_metrics = metrics
        return metrics

    def enhance_insights(
        self,
        insights: list,
        context: dict,
        tool_schema: dict,
        model: str = None
    ) -> Optional[dict]:
        if not self.is_available():
            return None

        model = model or self.MODELS['turbo']
        start_time = time.time()

        try:
            openai_tool = self._convert_to_openai_tool(tool_schema)

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": PROCUREMENT_SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": self._build_enhancement_prompt(insights, context)
                    }
                ],
                tools=[openai_tool],
                tool_choice={"type": "function", "function": {"name": tool_schema["name"]}},
                max_tokens=2048
            )

            metrics = self._extract_metrics(response, model, 'enhance', start_time)
            logger.info(
                f"OpenAI enhance: {metrics.tokens_input} in, {metrics.tokens_output} out, "
                f"cost: ${metrics.cost_usd}"
            )

            if response.choices and response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]
                result = json.loads(tool_call.function.arguments)
                result['provider'] = 'openai'
                result['model'] = model
                result['generated_at'] = datetime.now().isoformat()
                result['_metrics'] = {
                    'tokens_input': metrics.tokens_input,
                    'tokens_output': metrics.tokens_output,
                    'cost_usd': float(metrics.cost_usd),
                    'latency_ms': metrics.latency_ms,
                }
                return result

            logger.warning("OpenAI did not return function call response")
            return None

        except Exception as e:
            self._last_metrics = LLMRequestMetrics(
                provider='openai',
                model=model,
                model_tier='gpt4_turbo',
                request_type='enhance',
                latency_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )
            logger.error(f"OpenAI enhancement failed: {e}")
            raise

    def analyze_single_insight(
        self,
        insight: dict,
        tool_schema: dict,
        model: str = None
    ) -> Optional[dict]:
        if not self.is_available():
            return None

        model = model or self.MODELS['mini']
        start_time = time.time()

        try:
            openai_tool = self._convert_to_openai_tool(tool_schema)

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": PROCUREMENT_SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": self._build_single_insight_prompt(insight)
                    }
                ],
                tools=[openai_tool],
                tool_choice={"type": "function", "function": {"name": tool_schema["name"]}},
                max_tokens=500
            )

            metrics = self._extract_metrics(response, model, 'single_insight', start_time)

            if response.choices and response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]
                result = json.loads(tool_call.function.arguments)
                result['provider'] = 'openai'
                result['model'] = model
                result['generated_at'] = datetime.now().isoformat()
                result['_metrics'] = {
                    'tokens_input': metrics.tokens_input,
                    'tokens_output': metrics.tokens_output,
                    'cost_usd': float(metrics.cost_usd),
                    'latency_ms': metrics.latency_ms,
                }
                return result

            return None

        except Exception as e:
            self._last_metrics = LLMRequestMetrics(
                provider='openai',
                model=model,
                model_tier='gpt4o_mini',
                request_type='single_insight',
                latency_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )
            logger.error(f"OpenAI single insight analysis failed: {e}")
            raise

    def deep_analysis(
        self,
        insight_data: dict,
        context: dict,
        tool_schema: dict,
        model: str = None
    ) -> Optional[dict]:
        if not self.is_available():
            return None

        model = model or self.MODELS['turbo']
        start_time = time.time()

        try:
            openai_tool = self._convert_to_openai_tool(tool_schema)

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": PROCUREMENT_SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": self._build_deep_analysis_prompt(insight_data, context)
                    }
                ],
                tools=[openai_tool],
                tool_choice={"type": "function", "function": {"name": tool_schema["name"]}},
                max_tokens=4096
            )

            metrics = self._extract_metrics(response, model, 'deep_analysis', start_time)
            logger.info(
                f"OpenAI deep_analysis: {metrics.tokens_input} in, {metrics.tokens_output} out, "
                f"cost: ${metrics.cost_usd}"
            )

            if response.choices and response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]
                result = json.loads(tool_call.function.arguments)
                result['insight_id'] = insight_data.get('id')
                result['provider'] = 'openai'
                result['model'] = model
                result['generated_at'] = datetime.now().isoformat()
                result['_metrics'] = {
                    'tokens_input': metrics.tokens_input,
                    'tokens_output': metrics.tokens_output,
                    'cost_usd': float(metrics.cost_usd),
                    'latency_ms': metrics.latency_ms,
                }
                return result

            return None

        except Exception as e:
            self._last_metrics = LLMRequestMetrics(
                provider='openai',
                model=model,
                model_tier='gpt4_turbo',
                request_type='deep_analysis',
                latency_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )
            logger.error(f"OpenAI deep analysis failed: {e}")
            raise

    def _build_enhancement_prompt(self, insights: list, context: dict) -> str:
        return f"""Analyze these procurement insights and provide structured recommendations.

Organization: {context['organization']['name']}

Spending Summary:
- Total YTD Spend: ${context['spending']['total_ytd']:,.2f}
- Supplier Count: {context['spending']['supplier_count']}
- Category Count: {context['spending']['category_count']}

Current Insights ({len(insights)} total):
{json.dumps(context.get('insights', insights[:15]), indent=2)}

Provide actionable recommendations prioritized by impact and effort."""

    def _build_single_insight_prompt(self, insight: dict) -> str:
        return f"""Analyze this procurement insight:

Type: {insight['type']}
Title: {insight['title']}
Description: {insight['description']}
Severity: {insight['severity']}
Potential Savings: ${insight.get('potential_savings', 0):,.2f}

Provide root cause analysis and actionable remediation steps."""

    def _build_deep_analysis_prompt(self, insight_data: dict, context: dict) -> str:
        return f"""Perform a comprehensive deep analysis of this procurement insight.

INSIGHT DETAILS:
- Type: {insight_data.get('type', 'N/A')}
- Title: {insight_data.get('title', 'N/A')}
- Description: {insight_data.get('description', 'N/A')}
- Severity: {insight_data.get('severity', 'N/A')}
- Potential Savings: ${insight_data.get('potential_savings', 0):,.2f}

CONTEXT:
{json.dumps(context, indent=2)}

Provide thorough analysis with root cause, implementation roadmap, financial impact, risks, and next steps."""


class AIProviderManager:
    """
    Manages AI providers with automatic failover, semantic caching, RAG, and request logging.

    Features:
    - Automatic failover between providers
    - Semantic caching for 73% cost reduction on similar queries
    - RAG (Retrieval-Augmented Generation) for context augmentation
    - Request logging to LLMRequestLog for cost tracking
    - Metrics collection from provider responses
    - Tiered model selection support
    """

    PROVIDER_CLASSES = {
        'anthropic': AnthropicProvider,
        'openai': OpenAIProvider,
    }

    def __init__(
        self,
        primary_provider: str,
        api_keys: Dict[str, str],
        fallback_order: List[str] = None,
        enable_fallback: bool = True,
        organization_id: Optional[int] = None,
        enable_logging: bool = True,
        enable_semantic_cache: bool = True,
        enable_rag: bool = True,
        enable_validation: bool = True
    ):
        """
        Initialize the provider manager.

        Args:
            primary_provider: Primary provider name ('anthropic' or 'openai')
            api_keys: Dict mapping provider names to API keys
            fallback_order: Order of providers to try (defaults to ['anthropic', 'openai'])
            enable_fallback: Whether to enable automatic failover
            organization_id: Organization ID for request logging
            enable_logging: Whether to log requests to LLMRequestLog
            enable_semantic_cache: Whether to use semantic caching
            enable_rag: Whether to use RAG for context augmentation
            enable_validation: Whether to validate LLM responses against source data
        """
        self.primary_provider = primary_provider
        self.api_keys = api_keys or {}
        self.fallback_order = fallback_order or ['anthropic', 'openai']
        self.enable_fallback = enable_fallback
        self.organization_id = organization_id
        self.enable_logging = enable_logging
        self.enable_semantic_cache = enable_semantic_cache
        self.enable_rag = enable_rag
        self.enable_validation = enable_validation

        self._providers: Dict[str, AIProvider] = {}
        self._provider_errors: Dict[str, str] = {}
        self._last_successful_provider: Optional[str] = None
        self._semantic_cache = None
        self._rag_service = None
        self._validator = None

        self._initialize_providers()
        self._initialize_semantic_cache()
        self._initialize_rag()
        self._initialize_validator()

    def _initialize_providers(self) -> None:
        """Initialize all available providers."""
        for name, api_key in self.api_keys.items():
            if api_key and name in self.PROVIDER_CLASSES:
                try:
                    self._providers[name] = self.PROVIDER_CLASSES[name](api_key)
                    logger.info(f"Initialized {name} provider")
                except Exception as e:
                    logger.warning(f"Failed to initialize {name} provider: {e}")
                    self._provider_errors[name] = str(e)

    def _initialize_semantic_cache(self) -> None:
        """Initialize semantic cache service if enabled."""
        if not self.enable_semantic_cache or not self.organization_id:
            return

        try:
            from .semantic_cache import SemanticCacheService
            openai_key = self.api_keys.get('openai')
            self._semantic_cache = SemanticCacheService(
                organization_id=self.organization_id,
                openai_api_key=openai_key
            )
            logger.info("Initialized semantic cache service")
        except Exception as e:
            logger.warning(f"Failed to initialize semantic cache: {e}")
            self._semantic_cache = None

    def _initialize_rag(self) -> None:
        """Initialize RAG service if enabled."""
        if not self.enable_rag or not self.organization_id:
            return

        try:
            from .rag_service import RAGService
            openai_key = self.api_keys.get('openai')
            self._rag_service = RAGService(
                organization_id=self.organization_id,
                openai_api_key=openai_key
            )
            logger.info("Initialized RAG service")
        except Exception as e:
            logger.warning(f"Failed to initialize RAG service: {e}")
            self._rag_service = None

    def _initialize_validator(self) -> None:
        """Initialize response validator if enabled."""
        if not self.enable_validation or not self.organization_id:
            return

        try:
            from .ai_validation import LLMResponseValidator
            self._validator = LLMResponseValidator(
                organization_id=self.organization_id
            )
            logger.info("Initialized LLM response validator")
        except Exception as e:
            logger.warning(f"Failed to initialize validator: {e}")
            self._validator = None

    def _validate_and_adjust_response(
        self,
        response: dict,
        source_data: Optional[dict] = None,
        request_type: str = 'enhance'
    ) -> dict:
        """
        Validate LLM response and adjust confidence scores.

        Args:
            response: The AI-generated response to validate
            source_data: Source data context for validation
            request_type: Type of request for logging

        Returns:
            Response with validation metadata added
        """
        if not self._validator:
            return response

        try:
            validation = self._validator.validate(response, source_data)

            response['_validation'] = {
                'validated': validation['validated'],
                'confidence_original': validation['confidence_original'],
                'confidence_adjusted': validation['confidence_adjusted'],
                'issues_count': validation['total_issues'],
                'critical_count': validation['critical_count'],
            }

            if validation['errors']:
                response['_validation']['issues'] = validation['errors'][:5]

            if not validation['validated']:
                logger.warning(
                    f"LLM response validation failed for {request_type}: "
                    f"{validation['critical_count']} critical, {validation['error_count']} errors"
                )

        except Exception as e:
            logger.error(f"Validation failed with exception: {e}")

        return response

    def _augment_context_with_rag(
        self,
        context: dict,
        insights: list = None,
        query: str = None
    ) -> dict:
        """
        Augment context with relevant documents from RAG.

        Args:
            context: Base context to augment
            insights: Optional list of insights to derive query from
            query: Optional explicit query for RAG search

        Returns:
            Augmented context dict with 'relevant_documents' key
        """
        if not self._rag_service:
            return context

        try:
            if not query and insights:
                query_parts = []
                for insight in insights[:3]:
                    query_parts.append(
                        f"{insight.get('type', '')} {insight.get('title', '')}"
                    )
                query = ' '.join(query_parts)

            if query:
                context = self._rag_service.augment_context(
                    query=query,
                    base_context=context,
                    max_content_length=400
                )

        except Exception as e:
            logger.warning(f"RAG augmentation failed: {e}")

        return context

    def _build_cache_key(self, insights: list, context: dict) -> str:
        """Build a cache key from insights and context."""
        key_parts = [
            json.dumps([{
                'type': i.get('type'),
                'title': i.get('title'),
                'severity': i.get('severity')
            } for i in insights[:10]], sort_keys=True),
            str(context.get('spending', {}).get('total_ytd', 0)),
            str(context.get('spending', {}).get('supplier_count', 0)),
        ]
        return '|'.join(key_parts)

    def _get_providers_to_try(self) -> List[str]:
        """Get ordered list of providers to attempt."""
        providers = [self.primary_provider]
        if self.enable_fallback:
            providers.extend(p for p in self.fallback_order if p != self.primary_provider)
        return providers

    def _log_request(
        self,
        metrics: LLMRequestMetrics,
        cache_hit: bool = False,
        validation_passed: bool = True,
        validation_errors: List = None
    ) -> None:
        """
        Log LLM request to database for cost tracking.

        Args:
            metrics: LLMRequestMetrics from provider call
            cache_hit: Whether response was from semantic cache
            validation_passed: Whether hallucination validation passed
            validation_errors: List of validation errors if any
        """
        if not self.enable_logging:
            return

        try:
            from .models import LLMRequestLog

            LLMRequestLog.objects.create(
                organization_id=self.organization_id,
                request_type=metrics.request_type,
                model_used=metrics.model,
                model_tier=metrics.model_tier,
                provider=metrics.provider,
                tokens_input=metrics.tokens_input,
                tokens_output=metrics.tokens_output,
                latency_ms=metrics.latency_ms,
                cost_usd=metrics.cost_usd,
                cache_hit=cache_hit,
                prompt_cache_read_tokens=metrics.prompt_cache_read_tokens,
                prompt_cache_write_tokens=metrics.prompt_cache_write_tokens,
                validation_passed=validation_passed,
                validation_errors=validation_errors or [],
                error_occurred=bool(metrics.error),
                error_message=metrics.error or '',
            )
        except Exception as e:
            logger.warning(f"Failed to log LLM request: {e}")

    def get_provider(self, name: str) -> Optional[AIProvider]:
        """Get a specific provider instance."""
        return self._providers.get(name)

    def get_available_providers(self) -> List[str]:
        """Get list of available (configured) providers."""
        return [name for name, provider in self._providers.items() if provider.is_available()]

    def health_check_all(self) -> Dict[str, dict]:
        """Perform health check on all providers."""
        results = {}
        for name, provider in self._providers.items():
            results[name] = provider.health_check()
        return results

    def enhance_insights(
        self,
        insights: list,
        context: dict,
        tool_schema: dict,
        skip_cache: bool = False,
        skip_rag: bool = False
    ) -> Optional[dict]:
        """
        Enhance insights with RAG, semantic caching, automatic failover, and logging.

        Args:
            insights: List of insight dictionaries
            context: Comprehensive context for AI analysis
            tool_schema: Tool/function schema for structured output
            skip_cache: Whether to skip semantic cache lookup
            skip_rag: Whether to skip RAG context augmentation

        Returns:
            Enhancement dict with 'provider' field indicating which provider succeeded,
            or None if all providers fail
        """
        cache_key = self._build_cache_key(insights, context)

        if self._semantic_cache and not skip_cache:
            cached = self._semantic_cache.lookup(cache_key, request_type='enhance')
            if cached:
                logger.info("Semantic cache hit for enhance_insights")
                cached['_cache_hit'] = True
                return cached

        if not skip_rag:
            context = self._augment_context_with_rag(context, insights=insights)

        providers_to_try = self._get_providers_to_try()
        last_error = None

        for provider_name in providers_to_try:
            provider = self._providers.get(provider_name)
            if not provider or not provider.is_available():
                logger.debug(f"Skipping unavailable provider: {provider_name}")
                continue

            try:
                logger.info(f"Attempting insight enhancement with {provider_name}")
                result = provider.enhance_insights(insights, context, tool_schema)

                if result:
                    self._last_successful_provider = provider_name
                    logger.info(f"Enhancement succeeded with {provider_name}")

                    source_data = {
                        'total_spend': context.get('spending', {}).get('total_ytd', 0),
                        'insights': insights,
                    }
                    result = self._validate_and_adjust_response(
                        result, source_data, request_type='enhance'
                    )

                    validation_info = result.get('_validation', {})
                    if hasattr(provider, 'last_metrics') and provider.last_metrics:
                        self._log_request(
                            provider.last_metrics,
                            cache_hit=False,
                            validation_passed=validation_info.get('validated', True),
                            validation_errors=validation_info.get('issues', [])
                        )

                    if self._semantic_cache:
                        self._semantic_cache.store(
                            cache_key, result, request_type='enhance'
                        )

                    return result
                else:
                    if hasattr(provider, 'last_metrics') and provider.last_metrics:
                        self._log_request(provider.last_metrics, cache_hit=False)
            except Exception as e:
                last_error = e
                self._provider_errors[provider_name] = str(e)
                logger.warning(f"Provider {provider_name} failed: {e}")

                if hasattr(provider, 'last_metrics') and provider.last_metrics:
                    self._log_request(provider.last_metrics)

                if not self.enable_fallback:
                    break
                continue

        logger.error(f"All providers failed for enhancement. Last error: {last_error}")
        return None

    def analyze_single_insight(
        self,
        insight: dict,
        tool_schema: dict,
        skip_cache: bool = False
    ) -> Optional[dict]:
        """Analyze single insight with semantic caching, automatic failover, and logging."""
        cache_key = json.dumps({
            'type': insight.get('type'),
            'title': insight.get('title'),
            'severity': insight.get('severity'),
            'savings': insight.get('potential_savings', 0)
        }, sort_keys=True)

        if self._semantic_cache and not skip_cache:
            cached = self._semantic_cache.lookup(cache_key, request_type='single_insight')
            if cached:
                logger.info("Semantic cache hit for analyze_single_insight")
                cached['_cache_hit'] = True
                return cached

        providers_to_try = self._get_providers_to_try()
        last_error = None

        for provider_name in providers_to_try:
            provider = self._providers.get(provider_name)
            if not provider or not provider.is_available():
                continue

            try:
                logger.debug(f"Attempting single insight analysis with {provider_name}")
                result = provider.analyze_single_insight(insight, tool_schema)

                if result:
                    self._last_successful_provider = provider_name

                    source_data = {'insights': [insight]}
                    result = self._validate_and_adjust_response(
                        result, source_data, request_type='single_insight'
                    )

                    validation_info = result.get('_validation', {})
                    if hasattr(provider, 'last_metrics') and provider.last_metrics:
                        self._log_request(
                            provider.last_metrics,
                            cache_hit=False,
                            validation_passed=validation_info.get('validated', True),
                            validation_errors=validation_info.get('issues', [])
                        )

                    if self._semantic_cache:
                        self._semantic_cache.store(
                            cache_key, result, request_type='single_insight'
                        )

                    return result
                else:
                    if hasattr(provider, 'last_metrics') and provider.last_metrics:
                        self._log_request(provider.last_metrics, cache_hit=False)
            except Exception as e:
                last_error = e
                self._provider_errors[provider_name] = str(e)
                logger.warning(f"Provider {provider_name} failed for single insight: {e}")

                if hasattr(provider, 'last_metrics') and provider.last_metrics:
                    self._log_request(provider.last_metrics)

                if not self.enable_fallback:
                    break
                continue

        logger.error(f"All providers failed for single insight. Last error: {last_error}")
        return None

    def deep_analysis(
        self,
        insight_data: dict,
        context: dict,
        tool_schema: dict,
        skip_cache: bool = False,
        skip_rag: bool = False
    ) -> Optional[dict]:
        """Perform deep analysis with RAG, semantic caching, automatic failover, and logging."""
        cache_key = json.dumps({
            'id': insight_data.get('id'),
            'type': insight_data.get('type'),
            'title': insight_data.get('title'),
            'total_ytd': context.get('spending', {}).get('total_ytd', 0)
        }, sort_keys=True)

        if self._semantic_cache and not skip_cache:
            cached = self._semantic_cache.lookup(cache_key, request_type='deep_analysis')
            if cached:
                logger.info("Semantic cache hit for deep_analysis")
                cached['_cache_hit'] = True
                return cached

        if not skip_rag:
            query = f"{insight_data.get('type', '')} {insight_data.get('title', '')} {insight_data.get('description', '')}"
            context = self._augment_context_with_rag(context, query=query)

        providers_to_try = self._get_providers_to_try()
        last_error = None

        for provider_name in providers_to_try:
            provider = self._providers.get(provider_name)
            if not provider or not provider.is_available():
                continue

            try:
                logger.info(f"Attempting deep analysis with {provider_name}")
                result = provider.deep_analysis(insight_data, context, tool_schema)

                if result:
                    self._last_successful_provider = provider_name
                    logger.info(f"Deep analysis succeeded with {provider_name}")

                    source_data = {
                        'total_spend': context.get('spending', {}).get('total_ytd', 0),
                        'insights': [insight_data],
                    }
                    result = self._validate_and_adjust_response(
                        result, source_data, request_type='deep_analysis'
                    )

                    validation_info = result.get('_validation', {})
                    if hasattr(provider, 'last_metrics') and provider.last_metrics:
                        self._log_request(
                            provider.last_metrics,
                            cache_hit=False,
                            validation_passed=validation_info.get('validated', True),
                            validation_errors=validation_info.get('issues', [])
                        )

                    if self._semantic_cache:
                        self._semantic_cache.store(
                            cache_key, result, request_type='deep_analysis', ttl_hours=2
                        )

                    return result
                else:
                    if hasattr(provider, 'last_metrics') and provider.last_metrics:
                        self._log_request(provider.last_metrics, cache_hit=False)
            except Exception as e:
                last_error = e
                self._provider_errors[provider_name] = str(e)
                logger.warning(f"Provider {provider_name} failed for deep analysis: {e}")

                if hasattr(provider, 'last_metrics') and provider.last_metrics:
                    self._log_request(provider.last_metrics)

                if not self.enable_fallback:
                    break
                continue

        logger.error(f"All providers failed for deep analysis. Last error: {last_error}")
        return None

    def classify_query_complexity(self, query: str) -> str:
        """
        Classify query complexity using Anthropic provider.

        Returns: 'simple', 'standard', or 'complex'
        """
        anthropic_provider = self._providers.get('anthropic')
        if anthropic_provider and isinstance(anthropic_provider, AnthropicProvider):
            return anthropic_provider.classify_query_complexity(query)
        return 'standard'

    def select_model_for_task(self, task_type: str, complexity: str = None) -> str:
        """
        Select appropriate model for a task using Anthropic provider.

        Args:
            task_type: 'enhance', 'single_insight', 'deep_analysis', 'classify'
            complexity: Optional override - 'simple', 'standard', 'complex'

        Returns:
            Model identifier string
        """
        anthropic_provider = self._providers.get('anthropic')
        if anthropic_provider and isinstance(anthropic_provider, AnthropicProvider):
            return anthropic_provider.select_model_for_task(task_type, complexity)
        return 'claude-sonnet-4-20250514'

    def get_status(self) -> dict:
        """
        Get comprehensive status of all providers and semantic cache.

        Returns:
            Dict with provider and cache status information for monitoring
        """
        status = {
            "primary_provider": self.primary_provider,
            "fallback_enabled": self.enable_fallback,
            "last_successful_provider": self._last_successful_provider,
            "available_providers": self.get_available_providers(),
            "provider_errors": self._provider_errors.copy(),
            "providers": {
                name: {
                    "available": provider.is_available(),
                    "last_error": self._provider_errors.get(name)
                }
                for name, provider in self._providers.items()
            },
            "semantic_cache": {
                "enabled": self.enable_semantic_cache,
                "initialized": self._semantic_cache is not None,
            },
            "rag": {
                "enabled": self.enable_rag,
                "initialized": self._rag_service is not None,
            },
            "validation": {
                "enabled": self.enable_validation,
                "initialized": self._validator is not None,
            }
        }

        if self._semantic_cache:
            try:
                status["semantic_cache"]["stats"] = self._semantic_cache.get_stats()
            except Exception as e:
                status["semantic_cache"]["stats_error"] = str(e)

        if self._rag_service:
            try:
                status["rag"]["stats"] = self._rag_service.get_stats()
            except Exception as e:
                status["rag"]["stats_error"] = str(e)

        return status

    def invalidate_cache(self, request_type: str = None) -> int:
        """
        Invalidate semantic cache entries.

        Args:
            request_type: Optional type filter (invalidate all if None)

        Returns:
            Number of entries invalidated
        """
        if not self._semantic_cache:
            return 0
        return self._semantic_cache.invalidate(request_type=request_type)
