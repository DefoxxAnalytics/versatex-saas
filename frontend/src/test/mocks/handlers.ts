/**
 * MSW handlers for API mocking in tests
 */
import { http, HttpResponse } from "msw";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

// Mock user data
const mockUser = {
  id: 1,
  username: "testuser",
  email: "test@example.com",
  first_name: "Test",
  last_name: "User",
  profile: {
    id: 1,
    organization: {
      id: 1,
      name: "Test Organization",
      slug: "test-org",
    },
    role: "admin",
    is_active: true,
  },
};

// Mock suppliers
const mockSuppliers = [
  {
    id: 1,
    name: "Supplier A",
    code: "SUP-A",
    contact_email: "a@supplier.com",
    is_active: true,
    transaction_count: 10,
    total_spend: "50000.00",
  },
  {
    id: 2,
    name: "Supplier B",
    code: "SUP-B",
    contact_email: "b@supplier.com",
    is_active: true,
    transaction_count: 5,
    total_spend: "25000.00",
  },
];

// Mock categories
const mockCategories = [
  {
    id: 1,
    name: "Office Supplies",
    description: "Office supplies and stationery",
    is_active: true,
    transaction_count: 8,
    total_spend: "15000.00",
  },
  {
    id: 2,
    name: "IT Equipment",
    description: "Computers and IT equipment",
    is_active: true,
    transaction_count: 6,
    total_spend: "45000.00",
  },
];

// Mock transactions
const mockTransactions = [
  {
    id: 1,
    supplier: 1,
    supplier_name: "Supplier A",
    category: 1,
    category_name: "Office Supplies",
    amount: "1500.00",
    date: "2024-01-15",
    description: "Monthly supplies",
    invoice_number: "INV-001",
  },
  {
    id: 2,
    supplier: 2,
    supplier_name: "Supplier B",
    category: 2,
    category_name: "IT Equipment",
    amount: "25000.00",
    date: "2024-01-20",
    description: "New laptops",
    invoice_number: "INV-002",
  },
];

// Mock analytics overview
const mockOverviewStats = {
  total_spend: 75000.0,
  transaction_count: 15,
  supplier_count: 2,
  category_count: 2,
  avg_transaction: 5000.0,
};

// Mock spend by category
const mockSpendByCategory = [
  { category: "IT Equipment", amount: 45000.0, count: 6 },
  { category: "Office Supplies", amount: 15000.0, count: 8 },
];

// Mock monthly trend
const mockMonthlyTrend = [
  { month: "2024-01", amount: 25000.0, count: 5 },
  { month: "2024-02", amount: 30000.0, count: 6 },
  { month: "2024-03", amount: 20000.0, count: 4 },
];

export const handlers = [
  // Authentication handlers
  http.post(`${API_URL}/v1/auth/login/`, async ({ request }) => {
    const body = (await request.json()) as {
      username?: string;
      password?: string;
    };
    if (body.username === "testuser" && body.password === "TestPass123!") {
      return HttpResponse.json(
        {
          user: mockUser,
          message: "Login successful",
        },
        {
          headers: {
            "Set-Cookie": "access_token=mock-access-token; HttpOnly; Path=/",
          },
        },
      );
    }
    return HttpResponse.json({ error: "Invalid credentials" }, { status: 401 });
  }),

  http.post(`${API_URL}/v1/auth/logout/`, () => {
    return HttpResponse.json({ message: "Logout successful" });
  }),

  http.post(`${API_URL}/v1/auth/register/`, async ({ request }) => {
    const body = (await request.json()) as { username?: string };
    return HttpResponse.json(
      {
        user: { ...mockUser, username: body.username || "newuser" },
        message: "User registered successfully",
      },
      { status: 201 },
    );
  }),

  http.get(`${API_URL}/v1/auth/user/`, () => {
    return HttpResponse.json(mockUser);
  }),

  http.post(`${API_URL}/v1/auth/token/refresh/`, () => {
    return HttpResponse.json({ message: "Token refreshed successfully" });
  }),

  // Procurement handlers
  http.get(`${API_URL}/v1/procurement/suppliers/`, () => {
    return HttpResponse.json(mockSuppliers);
  }),

  http.post(`${API_URL}/v1/procurement/suppliers/`, async ({ request }) => {
    const body = (await request.json()) as { name?: string };
    return HttpResponse.json(
      { id: 3, ...body, is_active: true },
      { status: 201 },
    );
  }),

  http.get(`${API_URL}/v1/procurement/suppliers/:id/`, ({ params }) => {
    const supplier = mockSuppliers.find((s) => s.id === Number(params.id));
    if (supplier) {
      return HttpResponse.json(supplier);
    }
    return HttpResponse.json({ error: "Not found" }, { status: 404 });
  }),

  http.get(`${API_URL}/v1/procurement/categories/`, () => {
    return HttpResponse.json(mockCategories);
  }),

  http.post(`${API_URL}/v1/procurement/categories/`, async ({ request }) => {
    const body = (await request.json()) as { name?: string };
    return HttpResponse.json(
      { id: 3, ...body, is_active: true },
      { status: 201 },
    );
  }),

  http.get(`${API_URL}/v1/procurement/transactions/`, () => {
    return HttpResponse.json(mockTransactions);
  }),

  http.post(`${API_URL}/v1/procurement/transactions/`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ id: 3, ...body }, { status: 201 });
  }),

  http.post(`${API_URL}/v1/procurement/transactions/upload_csv/`, () => {
    return HttpResponse.json(
      {
        id: 1,
        file_name: "upload.csv",
        batch_id: "batch-001",
        total_rows: 100,
        successful_rows: 98,
        failed_rows: 2,
        duplicate_rows: 0,
        status: "completed",
      },
      { status: 201 },
    );
  }),

  http.post(
    `${API_URL}/v1/procurement/transactions/bulk_delete/`,
    async ({ request }) => {
      const body = (await request.json()) as { ids?: number[] };
      const ids = body.ids || [];
      return HttpResponse.json({
        message: `${ids.length} transactions deleted successfully`,
        count: ids.length,
      });
    },
  ),

  http.get(`${API_URL}/v1/procurement/transactions/export/`, () => {
    return new HttpResponse(
      "supplier,category,amount,date\nTest,Test,1000,2024-01-01",
      {
        headers: {
          "Content-Type": "text/csv",
          "Content-Disposition": 'attachment; filename="transactions.csv"',
        },
      },
    );
  }),

  http.get(`${API_URL}/v1/procurement/uploads/`, () => {
    return HttpResponse.json([
      {
        id: 1,
        file_name: "data.csv",
        batch_id: "batch-001",
        total_rows: 100,
        successful_rows: 100,
        status: "completed",
        created_at: "2024-01-15T10:00:00Z",
      },
    ]);
  }),

  // Procurement handlers (non-versioned)
  http.get(`${API_URL}/procurement/suppliers/`, () => {
    return HttpResponse.json(mockSuppliers);
  }),

  http.get(`${API_URL}/procurement/categories/`, () => {
    return HttpResponse.json(mockCategories);
  }),

  http.get(`${API_URL}/procurement/transactions/`, () => {
    return HttpResponse.json(mockTransactions);
  }),

  // Analytics handlers (non-versioned - used by actual API)
  http.get(`${API_URL}/analytics/overview/`, () => {
    return HttpResponse.json(mockOverviewStats);
  }),

  http.get(`${API_URL}/analytics/spend-by-category/`, () => {
    return HttpResponse.json(mockSpendByCategory);
  }),

  http.get(`${API_URL}/analytics/spend-by-supplier/`, () => {
    return HttpResponse.json([
      { supplier: "Supplier A", amount: 50000.0, count: 10 },
      { supplier: "Supplier B", amount: 25000.0, count: 5 },
    ]);
  }),

  http.get(`${API_URL}/analytics/monthly-trend/`, () => {
    return HttpResponse.json(mockMonthlyTrend);
  }),

  http.get(`${API_URL}/analytics/pareto/`, () => {
    return HttpResponse.json([
      { supplier: "Supplier A", amount: 50000.0, cumulative_percentage: 66.67 },
      { supplier: "Supplier B", amount: 25000.0, cumulative_percentage: 100.0 },
    ]);
  }),

  http.get(`${API_URL}/analytics/tail-spend/`, () => {
    return HttpResponse.json({
      tail_suppliers: [
        { supplier: "Supplier B", amount: 25000.0, transaction_count: 5 },
      ],
      tail_count: 1,
      tail_spend: 25000.0,
      tail_percentage: 33.33,
    });
  }),

  http.get(`${API_URL}/analytics/stratification/`, () => {
    return HttpResponse.json({
      strategic: [
        { category: "IT Equipment", spend: 45000.0, supplier_count: 1 },
      ],
      leverage: [],
      bottleneck: [],
      tactical: [
        { category: "Office Supplies", spend: 15000.0, supplier_count: 2 },
      ],
    });
  }),

  http.get(`${API_URL}/analytics/seasonality/`, () => {
    return HttpResponse.json([
      { month: "Jan", average_spend: 25000.0, occurrences: 1 },
      { month: "Feb", average_spend: 30000.0, occurrences: 1 },
      { month: "Mar", average_spend: 20000.0, occurrences: 1 },
      { month: "Apr", average_spend: 0, occurrences: 0 },
      { month: "May", average_spend: 0, occurrences: 0 },
      { month: "Jun", average_spend: 0, occurrences: 0 },
      { month: "Jul", average_spend: 0, occurrences: 0 },
      { month: "Aug", average_spend: 0, occurrences: 0 },
      { month: "Sep", average_spend: 0, occurrences: 0 },
      { month: "Oct", average_spend: 0, occurrences: 0 },
      { month: "Nov", average_spend: 0, occurrences: 0 },
      { month: "Dec", average_spend: 0, occurrences: 0 },
    ]);
  }),

  http.get(`${API_URL}/analytics/yoy/`, () => {
    return HttpResponse.json([
      {
        year: 2023,
        total_spend: 500000.0,
        transaction_count: 100,
        avg_transaction: 5000.0,
      },
      {
        year: 2024,
        total_spend: 75000.0,
        transaction_count: 15,
        avg_transaction: 5000.0,
        growth_percentage: -85.0,
      },
    ]);
  }),

  http.get(`${API_URL}/analytics/year-over-year/`, () => {
    return HttpResponse.json([
      {
        year: 2023,
        total_spend: 500000.0,
        transaction_count: 100,
        avg_transaction: 5000.0,
      },
      {
        year: 2024,
        total_spend: 75000.0,
        transaction_count: 15,
        avg_transaction: 5000.0,
        growth_percentage: -85.0,
      },
    ]);
  }),

  http.get(`${API_URL}/analytics/consolidation/`, () => {
    return HttpResponse.json([
      {
        category: "Office Supplies",
        supplier_count: 3,
        total_spend: 15000.0,
        suppliers: [
          { name: "Supplier A", spend: 8000.0 },
          { name: "Supplier B", spend: 5000.0 },
          { name: "Supplier C", spend: 2000.0 },
        ],
        potential_savings: 1500.0,
      },
    ]);
  }),

  http.get(`${API_URL}/analytics/categories/detailed/`, () => {
    return HttpResponse.json([
      {
        id: 1,
        name: "IT Equipment",
        total_spend: 45000.0,
        transaction_count: 6,
        supplier_count: 2,
        subcategories: ["Hardware", "Software"],
        risk_level: "low",
      },
      {
        id: 2,
        name: "Office Supplies",
        total_spend: 15000.0,
        transaction_count: 8,
        supplier_count: 3,
        subcategories: ["Paper", "Pens"],
        risk_level: "low",
      },
    ]);
  }),

  http.get(`${API_URL}/analytics/suppliers/detailed/`, () => {
    return HttpResponse.json([
      {
        id: 1,
        name: "Supplier A",
        total_spend: 50000.0,
        transaction_count: 10,
        category_count: 2,
        hhi_score: 0.35,
        concentration: "moderate",
      },
      {
        id: 2,
        name: "Supplier B",
        total_spend: 25000.0,
        transaction_count: 5,
        category_count: 1,
        hhi_score: 0.15,
        concentration: "low",
      },
    ]);
  }),

  // Analytics handlers (versioned - legacy)
  http.get(`${API_URL}/v1/analytics/overview/`, () => {
    return HttpResponse.json(mockOverviewStats);
  }),

  http.get(`${API_URL}/v1/analytics/spend-by-category/`, () => {
    return HttpResponse.json(mockSpendByCategory);
  }),

  http.get(`${API_URL}/v1/analytics/spend-by-supplier/`, () => {
    return HttpResponse.json([
      { supplier: "Supplier A", amount: 50000.0, count: 10 },
      { supplier: "Supplier B", amount: 25000.0, count: 5 },
    ]);
  }),

  http.get(`${API_URL}/v1/analytics/monthly-trend/`, () => {
    return HttpResponse.json(mockMonthlyTrend);
  }),

  http.get(`${API_URL}/v1/analytics/pareto/`, () => {
    return HttpResponse.json([
      { supplier: "Supplier A", amount: 50000.0, cumulative_percentage: 66.67 },
      { supplier: "Supplier B", amount: 25000.0, cumulative_percentage: 100.0 },
    ]);
  }),

  http.get(`${API_URL}/v1/analytics/tail-spend/`, () => {
    return HttpResponse.json({
      tail_suppliers: [
        { supplier: "Supplier B", amount: 25000.0, transaction_count: 5 },
      ],
      tail_count: 1,
      tail_spend: 25000.0,
      tail_percentage: 33.33,
    });
  }),

  http.get(`${API_URL}/v1/analytics/stratification/`, () => {
    return HttpResponse.json({
      strategic: [
        { category: "IT Equipment", spend: 45000.0, supplier_count: 1 },
      ],
      leverage: [],
      bottleneck: [],
      tactical: [
        { category: "Office Supplies", spend: 15000.0, supplier_count: 2 },
      ],
    });
  }),

  http.get(`${API_URL}/v1/analytics/seasonality/`, () => {
    return HttpResponse.json([
      { month: "Jan", average_spend: 25000.0, occurrences: 1 },
      { month: "Feb", average_spend: 30000.0, occurrences: 1 },
      { month: "Mar", average_spend: 20000.0, occurrences: 1 },
      { month: "Apr", average_spend: 0, occurrences: 0 },
      { month: "May", average_spend: 0, occurrences: 0 },
      { month: "Jun", average_spend: 0, occurrences: 0 },
      { month: "Jul", average_spend: 0, occurrences: 0 },
      { month: "Aug", average_spend: 0, occurrences: 0 },
      { month: "Sep", average_spend: 0, occurrences: 0 },
      { month: "Oct", average_spend: 0, occurrences: 0 },
      { month: "Nov", average_spend: 0, occurrences: 0 },
      { month: "Dec", average_spend: 0, occurrences: 0 },
    ]);
  }),

  http.get(`${API_URL}/v1/analytics/yoy/`, () => {
    return HttpResponse.json([
      {
        year: 2023,
        total_spend: 500000.0,
        transaction_count: 100,
        avg_transaction: 5000.0,
      },
      {
        year: 2024,
        total_spend: 75000.0,
        transaction_count: 15,
        avg_transaction: 5000.0,
        growth_percentage: -85.0,
      },
    ]);
  }),

  http.get(`${API_URL}/v1/analytics/consolidation/`, () => {
    return HttpResponse.json([
      {
        category: "Office Supplies",
        supplier_count: 3,
        total_spend: 15000.0,
        suppliers: [
          { name: "Supplier A", spend: 8000.0 },
          { name: "Supplier B", spend: 5000.0 },
          { name: "Supplier C", spend: 2000.0 },
        ],
        potential_savings: 1500.0,
      },
    ]);
  }),

  // Detailed analytics endpoints
  http.get(`${API_URL}/v1/analytics/category-details/`, () => {
    return HttpResponse.json([
      {
        id: 1,
        name: "IT Equipment",
        total_spend: 45000.0,
        transaction_count: 6,
        supplier_count: 2,
        subcategories: ["Hardware", "Software"],
        risk_level: "low",
      },
      {
        id: 2,
        name: "Office Supplies",
        total_spend: 15000.0,
        transaction_count: 8,
        supplier_count: 3,
        subcategories: ["Paper", "Pens"],
        risk_level: "low",
      },
    ]);
  }),

  http.get(`${API_URL}/v1/analytics/supplier-details/`, () => {
    return HttpResponse.json([
      {
        id: 1,
        name: "Supplier A",
        total_spend: 50000.0,
        transaction_count: 10,
        category_count: 2,
        hhi_score: 0.35,
        concentration: "moderate",
      },
      {
        id: 2,
        name: "Supplier B",
        total_spend: 25000.0,
        transaction_count: 5,
        category_count: 1,
        hhi_score: 0.15,
        concentration: "low",
      },
    ]);
  }),

  // Drilldown analytics endpoints
  http.get(`${API_URL}/analytics/pareto/detailed/`, () => {
    return HttpResponse.json({
      suppliers: [
        {
          id: 1,
          name: "Supplier A",
          amount: 50000.0,
          cumulative_percentage: 66.67,
        },
        {
          id: 2,
          name: "Supplier B",
          amount: 25000.0,
          cumulative_percentage: 100.0,
        },
      ],
    });
  }),

  http.get(`${API_URL}/analytics/pareto/supplier/:id/`, ({ params }) => {
    return HttpResponse.json({
      supplier_id: Number(params.id),
      supplier_name: "Supplier A",
      total_spend: 50000.0,
      categories: [
        { id: 1, name: "IT Equipment", spend: 35000.0 },
        { id: 2, name: "Office Supplies", spend: 15000.0 },
      ],
    });
  }),

  http.get(`${API_URL}/analytics/tail-spend/detailed/`, () => {
    return HttpResponse.json({
      tail_suppliers: [
        { id: 2, name: "Supplier B", amount: 25000.0, transaction_count: 5 },
      ],
      tail_count: 1,
      tail_spend: 25000.0,
      tail_percentage: 33.33,
      threshold: 50000,
      consolidation_opportunities: [],
    });
  }),

  http.get(`${API_URL}/analytics/tail-spend/category/:id/`, ({ params }) => {
    return HttpResponse.json({
      category_id: Number(params.id),
      category_name: "Office Supplies",
      vendors: [
        { id: 1, name: "Supplier A", spend: 8000.0 },
        { id: 2, name: "Supplier B", spend: 5000.0 },
      ],
    });
  }),

  http.get(`${API_URL}/analytics/tail-spend/vendor/:id/`, ({ params }) => {
    return HttpResponse.json({
      vendor_id: Number(params.id),
      vendor_name: "Supplier B",
      categories: [{ id: 1, name: "Office Supplies", spend: 25000.0 }],
      locations: ["New York"],
      monthly_spend: [{ month: "2024-01", amount: 5000.0 }],
    });
  }),

  http.get(`${API_URL}/analytics/stratification/detailed/`, () => {
    return HttpResponse.json({
      segments: [
        { name: "strategic", count: 1, spend: 45000.0 },
        { name: "tactical", count: 1, spend: 15000.0 },
      ],
      bands: [{ name: "$10K-$50K", count: 2, spend: 60000.0 }],
    });
  }),

  http.get(
    `${API_URL}/analytics/stratification/segment/:segment/`,
    ({ params }) => {
      return HttpResponse.json({
        segment: params.segment,
        suppliers: [{ id: 1, name: "Supplier A", spend: 50000.0 }],
      });
    },
  ),

  http.get(`${API_URL}/analytics/stratification/band/:band/`, ({ params }) => {
    return HttpResponse.json({
      band: params.band,
      suppliers: [
        { id: 1, name: "Supplier A", spend: 50000.0 },
        { id: 2, name: "Supplier B", spend: 25000.0 },
      ],
    });
  }),

  http.get(`${API_URL}/analytics/seasonality/detailed/`, () => {
    return HttpResponse.json({
      monthly_data: [
        { month: "Jan", average_spend: 25000.0, index: 1.1 },
        { month: "Feb", average_spend: 30000.0, index: 1.3 },
        { month: "Mar", average_spend: 20000.0, index: 0.9 },
      ],
      categories: [{ id: 1, name: "IT Equipment", peak_month: "Jan" }],
    });
  }),

  http.get(`${API_URL}/analytics/seasonality/category/:id/`, ({ params }) => {
    return HttpResponse.json({
      category_id: Number(params.id),
      category_name: "IT Equipment",
      monthly_data: [{ month: "Jan", spend: 15000.0 }],
      suppliers: [{ id: 1, name: "Supplier A", spend: 15000.0 }],
    });
  }),

  http.get(`${API_URL}/analytics/year-over-year/detailed/`, () => {
    return HttpResponse.json({
      years: [
        { year: 2023, total_spend: 500000.0, transaction_count: 100 },
        {
          year: 2024,
          total_spend: 75000.0,
          transaction_count: 15,
          growth: -85.0,
        },
      ],
      top_gainers: [{ id: 1, name: "IT Equipment", growth: 10.0 }],
      top_decliners: [{ id: 2, name: "Office Supplies", growth: -20.0 }],
    });
  }),

  http.get(
    `${API_URL}/analytics/year-over-year/category/:id/`,
    ({ params }) => {
      return HttpResponse.json({
        category_id: Number(params.id),
        category_name: "IT Equipment",
        year1_spend: 40000.0,
        year2_spend: 45000.0,
        growth: 12.5,
        suppliers: [
          {
            id: 1,
            name: "Supplier A",
            year1_spend: 40000.0,
            year2_spend: 45000.0,
          },
        ],
      });
    },
  ),

  http.get(
    `${API_URL}/analytics/year-over-year/supplier/:id/`,
    ({ params }) => {
      return HttpResponse.json({
        supplier_id: Number(params.id),
        supplier_name: "Supplier A",
        year1_spend: 45000.0,
        year2_spend: 50000.0,
        growth: 11.1,
        categories: [
          {
            id: 1,
            name: "IT Equipment",
            year1_spend: 35000.0,
            year2_spend: 40000.0,
          },
        ],
      });
    },
  ),

  // Reports endpoints (non-versioned - used by actual API)
  http.get(`${API_URL}/reports/templates/`, () => {
    return HttpResponse.json([
      {
        id: "executive_summary",
        name: "Executive Summary",
        report_type: "executive_summary",
      },
      {
        id: "spend_analysis",
        name: "Spend Analysis",
        report_type: "spend_analysis",
      },
      {
        id: "supplier_performance",
        name: "Supplier Performance",
        report_type: "supplier_performance",
      },
    ]);
  }),

  http.post(`${API_URL}/reports/generate/`, () => {
    return HttpResponse.json(
      {
        id: "report-123",
        status: "completed",
        report_type: "spend_analysis",
        created_at: new Date().toISOString(),
      },
      { status: 201 },
    );
  }),

  http.get(`${API_URL}/reports/`, () => {
    return HttpResponse.json({
      results: [
        {
          id: "report-1",
          name: "Q4 2024 Analysis",
          report_type: "spend_analysis",
          status: "completed",
          created_at: "2024-01-15T10:00:00Z",
        },
      ],
      total: 1,
    });
  }),

  http.get(`${API_URL}/reports/:id/status/`, ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      status: "completed",
      progress: 100,
    });
  }),

  http.get(`${API_URL}/reports/:id/`, ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      name: "Test Report",
      report_type: "spend_analysis",
      report_format: "pdf",
      status: "completed",
      created_at: "2024-01-15T10:00:00Z",
      file_path: "/reports/test-report.pdf",
    });
  }),

  http.get(`${API_URL}/reports/schedules/`, () => {
    return HttpResponse.json([
      {
        id: "schedule-1",
        name: "Weekly Spend Report",
        report_type: "spend_analysis",
        frequency: "weekly",
        next_run: "2024-01-22T09:00:00Z",
        is_active: true,
      },
    ]);
  }),

  http.post(`${API_URL}/reports/schedules/`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      {
        id: "schedule-new",
        ...body,
        created_at: new Date().toISOString(),
      },
      { status: 201 },
    );
  }),

  http.post(`${API_URL}/reports/preview/`, () => {
    return HttpResponse.json({
      overview: {
        total_spend: 75000.0,
        transaction_count: 15,
        supplier_count: 2,
        category_count: 2,
      },
      top_categories: [
        { category: "IT Equipment", amount: 45000.0 },
        { category: "Office Supplies", amount: 15000.0 },
      ],
      top_suppliers: [
        { supplier: "Supplier A", amount: 50000.0 },
        { supplier: "Supplier B", amount: 25000.0 },
      ],
    });
  }),

  // Reports endpoints (versioned - legacy)
  http.get(`${API_URL}/v1/reports/templates/`, () => {
    return HttpResponse.json([
      {
        id: "executive_summary",
        name: "Executive Summary",
        report_type: "executive_summary",
      },
      {
        id: "spend_analysis",
        name: "Spend Analysis",
        report_type: "spend_analysis",
      },
      {
        id: "supplier_performance",
        name: "Supplier Performance",
        report_type: "supplier_performance",
      },
    ]);
  }),

  http.post(`${API_URL}/v1/reports/generate/`, () => {
    return HttpResponse.json(
      {
        id: "report-123",
        status: "completed",
        report_type: "spend_analysis",
        created_at: new Date().toISOString(),
      },
      { status: 201 },
    );
  }),

  http.get(`${API_URL}/v1/reports/`, () => {
    return HttpResponse.json({
      results: [
        {
          id: "report-1",
          name: "Q4 2024 Analysis",
          report_type: "spend_analysis",
          status: "completed",
          created_at: "2024-01-15T10:00:00Z",
        },
      ],
      total: 1,
    });
  }),

  http.get(`${API_URL}/v1/reports/:id/status/`, ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      status: "completed",
      progress: 100,
    });
  }),

  http.get(`${API_URL}/v1/reports/:id/`, ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      name: "Test Report",
      report_type: "spend_analysis",
      report_format: "pdf",
      status: "completed",
      created_at: "2024-01-15T10:00:00Z",
      file_path: "/reports/test-report.pdf",
    });
  }),

  http.get(`${API_URL}/v1/reports/schedules/`, () => {
    return HttpResponse.json([
      {
        id: "schedule-1",
        name: "Weekly Spend Report",
        report_type: "spend_analysis",
        frequency: "weekly",
        next_run: "2024-01-22T09:00:00Z",
        is_active: true,
      },
    ]);
  }),

  http.post(`${API_URL}/v1/reports/schedules/`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      {
        id: "schedule-new",
        ...body,
        created_at: new Date().toISOString(),
      },
      { status: 201 },
    );
  }),

  http.post(`${API_URL}/v1/reports/preview/`, () => {
    return HttpResponse.json({
      overview: {
        total_spend: 75000.0,
        transaction_count: 15,
        supplier_count: 2,
        category_count: 2,
      },
      top_categories: [
        { category: "IT Equipment", amount: 45000.0 },
        { category: "Office Supplies", amount: 15000.0 },
      ],
      top_suppliers: [
        { supplier: "Supplier A", amount: 50000.0 },
        { supplier: "Supplier B", amount: 25000.0 },
      ],
    });
  }),

  // Legacy API endpoints (backwards compatibility)
  http.post(`${API_URL}/auth/login/`, async ({ request }) => {
    const body = (await request.json()) as {
      username?: string;
      password?: string;
    };
    if (body.username === "testuser" && body.password === "TestPass123!") {
      return HttpResponse.json({ user: mockUser, message: "Login successful" });
    }
    return HttpResponse.json({ error: "Invalid credentials" }, { status: 401 });
  }),

  http.get(`${API_URL}/auth/user/`, () => {
    return HttpResponse.json(mockUser);
  }),
];
