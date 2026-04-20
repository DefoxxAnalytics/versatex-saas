# Page Migration Guide - IndexedDB to Django API

This guide shows you exactly how to migrate each analytics page from IndexedDB to the Django API.

## ✅ Already Completed

- **Overview.tsx** - Fully migrated and working
- **Login.tsx** - Complete
- **App.tsx** - Protected routes configured
- **API hooks** - All analytics endpoints ready in `src/hooks/useAnalytics.ts`

## 📋 Pages to Migrate

1. Categories.tsx
2. Suppliers.tsx
3. ParetoAnalysis.tsx
4. SpendStratification.tsx
5. Seasonality.tsx
6. YearOverYear.tsx
7. TailSpend.tsx
8. Home.tsx (upload functionality)

---

## Migration Pattern

Every page follows the same 3-step pattern:

### Step 1: Replace Imports

**Remove:**
```tsx
import { useFilteredProcurementData } from '@/hooks/useProcurementData';
import { useFilters } from '@/hooks/useFilters';
```

**Add:**
```tsx
import { useSpendByCategory, useSpendBySupplier, /* etc */ } from '@/hooks/useAnalytics';
```

### Step 2: Replace Data Fetching

**Old (IndexedDB):**
```tsx
const { data = [], isLoading } = useFilteredProcurementData();
```

**New (API):**
```tsx
const { data: categoryData = [], isLoading } = useSpendByCategory();
```

### Step 3: Update Data Structure

The API returns slightly different field names. Update your code:

**API Response Format:**
```typescript
// Category data
{
  category: string,
  amount: number,
  percentage: number,
  transaction_count: number
}

// Supplier data
{
  supplier: string,
  amount: number,
  percentage: number,
  transaction_count: number
}

// Monthly trend
{
  month: string,  // "2024-01"
  amount: number
}
```

---

## Page-by-Page Instructions

### 1. Categories.tsx

**Current data fetching:**
```tsx
const { data = [] } = useFilteredProcurementData();
```

**Replace with:**
```tsx
import { useSpendByCategory, useTransactions } from '@/hooks/useAnalytics';

const { data: categoryData = [], isLoading: categoryLoading } = useSpendByCategory();
const { data: transactions = [], isLoading: transactionsLoading } = useTransactions();

const isLoading = categoryLoading || transactionsLoading;
```

**Update calculations:**
```tsx
// Old: Calculated from raw data
const categoryData = data.reduce((acc, record) => { ... }, {});

// New: Already calculated by API
const categories = categoryData.map(cat => ({
  category: cat.category,
  totalSpend: cat.amount,
  percentage: cat.percentage,
  transactionCount: cat.transaction_count,
  // For subcategory analysis, filter transactions
  subcategories: transactions
    .filter(t => t.category === cat.category)
    .reduce((acc, t) => {
      // Your subcategory logic here
    }, {})
}));
```

---

### 2. Suppliers.tsx

**Replace:**
```tsx
const { data = [] } = useFilteredProcurementData();
```

**With:**
```tsx
import { useSpendBySupplier, useTransactions } from '@/hooks/useAnalytics';

const { data: supplierData = [], isLoading } = useSpendBySupplier();
const { data: transactions = [] } = useTransactions();
```

**Update supplier calculations:**
```tsx
// API already provides aggregated data
const suppliers = supplierData.map(sup => ({
  supplier: sup.supplier,
  totalSpend: sup.amount,
  percentage: sup.percentage,
  transactionCount: sup.transaction_count,
}));
```

---

### 3. ParetoAnalysis.tsx

**Replace:**
```tsx
const { data = [] } = useFilteredProcurementData();
```

**With:**
```tsx
import { useParetoAnalysis } from '@/hooks/useAnalytics';

const { data: paretoData, isLoading } = useParetoAnalysis();
```

**API Response:**
```typescript
{
  suppliers: [
    {
      supplier: string,
      amount: number,
      cumulative_percentage: number,
      rank: number
    }
  ],
  categories: [ /* same structure */ ],
  pareto_80_supplier_count: number,
  pareto_80_category_count: number
}
```

**Use directly:**
```tsx
const suppliers = paretoData?.suppliers || [];
const categories = paretoData?.categories || [];
const pareto80Count = paretoData?.pareto_80_supplier_count || 0;
```

---

### 4. SpendStratification.tsx

**Replace:**
```tsx
const { data = [] } = useFilteredProcurementData();
```

**With:**
```tsx
import { useStratification } from '@/hooks/useAnalytics';

const { data: stratData, isLoading } = useStratification();
```

**API Response:**
```typescript
{
  strategic: { categories: [...], total_spend: number },
  leverage: { categories: [...], total_spend: number },
  bottleneck: { categories: [...], total_spend: number },
  tactical: { categories: [...], total_spend: number }
}
```

**Use directly:**
```tsx
const strategicItems = stratData?.strategic.categories || [];
const leverageItems = stratData?.leverage.categories || [];
// etc.
```

---

### 5. Seasonality.tsx

**Replace:**
```tsx
const { data = [] } = useFilteredProcurementData();
```

**With:**
```tsx
import { useSeasonality } from '@/hooks/useAnalytics';

const { data: seasonData, isLoading } = useSeasonality();
```

**API Response:**
```typescript
{
  monthly_patterns: [
    { month: number, avg_spend: number, transaction_count: number }
  ],
  quarterly_patterns: [
    { quarter: string, total_spend: number }
  ],
  peak_month: string,
  low_month: string
}
```

---

### 6. YearOverYear.tsx

**Replace:**
```tsx
const { data = [] } = useFilteredProcurementData();
```

**With:**
```tsx
import { useYearOverYear } from '@/hooks/useAnalytics';

const { data: yoyData, isLoading } = useYearOverYear();
```

**API Response:**
```typescript
{
  comparison: [
    {
      month: string,
      current_year: number,
      previous_year: number,
      growth_rate: number
    }
  ],
  summary: {
    current_year_total: number,
    previous_year_total: number,
    overall_growth: number
  }
}
```

---

### 7. TailSpend.tsx

**Replace:**
```tsx
const { data = [] } = useFilteredProcurementData();
```

**With:**
```tsx
import { useTailSpend } from '@/hooks/useAnalytics';

const { data: tailData, isLoading } = useTailSpend(20); // 20% threshold
```

**API Response:**
```typescript
{
  tail_suppliers: [
    { supplier: string, amount: number, percentage: number }
  ],
  tail_categories: [
    { category: string, amount: number, percentage: number }
  ],
  tail_spend_total: number,
  tail_supplier_count: number,
  consolidation_opportunities: [...]
}
```

---

### 8. Home.tsx (Upload)

**Replace:**
```tsx
// Old CSV processing logic
const handleFileUpload = async (file: File) => {
  // Parse CSV
  // Save to IndexedDB
};
```

**With:**
```tsx
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { procurementAPI } from '@/lib/api';
import { toast } from 'sonner';

export default function Home() {
  const queryClient = useQueryClient();
  
  const uploadMutation = useMutation({
    mutationFn: (file: File) => procurementAPI.uploadCSV(file, true), // append mode
    onSuccess: (response) => {
      toast.success(`Successfully uploaded ${response.data.successful_rows} rows`);
      // Invalidate all queries to refresh data
      queryClient.invalidateQueries();
    },
    onError: (error: any) => {
      const errorMsg = error.response?.data?.error || 'Upload failed';
      toast.error(errorMsg);
      if (error.response?.data?.errors) {
        console.error('Upload errors:', error.response.data.errors);
      }
    },
  });

  const handleFileUpload = (file: File) => {
    if (!file) return;
    if (!file.name.endsWith('.csv')) {
      toast.error('Please upload a CSV file');
      return;
    }
    uploadMutation.mutate(file);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Upload Data</h1>
      
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
        <input
          type="file"
          accept=".csv"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFileUpload(file);
          }}
          className="hidden"
          id="file-upload"
        />
        <label
          htmlFor="file-upload"
          className="cursor-pointer inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          {uploadMutation.isPending ? 'Uploading...' : 'Choose CSV File'}
        </label>
      </div>
      
      {uploadMutation.isPending && (
        <div className="text-center">
          <div className="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto"></div>
          <p className="mt-2 text-gray-600">Processing upload...</p>
        </div>
      )}
    </div>
  );
}
```

---

## Common Patterns

### Loading States

```tsx
if (isLoading) {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Loading analytics...</p>
      </div>
    </div>
  );
}
```

### Empty States

```tsx
if (!data || data.length === 0) {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="text-center">
        <Package className="h-16 w-16 text-gray-400 mx-auto mb-4" />
        <h2 className="text-2xl font-semibold mb-2">No Data Available</h2>
        <p className="text-gray-600 mb-4">Upload procurement data to see analytics</p>
        <Link href="/upload">
          <a className="px-4 py-2 bg-blue-600 text-white rounded-md">Upload Data</a>
        </Link>
      </div>
    </div>
  );
}
```

### Error Handling

```tsx
const { data, isLoading, error } = useSpendByCategory();

if (error) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-6">
      <h3 className="text-red-900 font-semibold">Error Loading Data</h3>
      <p className="text-red-700 mt-2">{error.message}</p>
    </div>
  );
}
```

---

## Testing Checklist

After migrating each page:

- [ ] Page loads without errors
- [ ] Loading state displays correctly
- [ ] Empty state shows when no data
- [ ] Data displays in charts/tables
- [ ] All calculations are correct
- [ ] No console errors
- [ ] Navigation works
- [ ] Responsive design intact

---

## Quick Reference: Available Hooks

```tsx
// From src/hooks/useAnalytics.ts

useOverviewStats()          // Overview statistics
useSpendByCategory()        // Category breakdown
useSpendBySupplier()        // Supplier breakdown
useMonthlyTrend(months)     // Trend analysis
useParetoAnalysis()         // 80/20 analysis
useTailSpend(threshold)     // Tail spend analysis
useStratification()         // Kraljic matrix
useSeasonality()            // Seasonal patterns
useYearOverYear()           // YoY comparison
useConsolidation()          // Consolidation opportunities
useTransactions(params)     // Raw transaction data
useSuppliers()              // Supplier list
useCategories()             // Category list
```

---

## Need Help?

1. Check the **Overview.tsx** file - it's fully migrated and shows the complete pattern
2. Look at **src/lib/api.ts** to see available API endpoints
3. Check **backend API docs** at http://localhost:8000/api/docs
4. Test API endpoints with curl before integrating

---

## Estimated Time

- Each simple page: 15-30 minutes
- Complex pages (Categories, TailSpend): 30-60 minutes
- Total for all 8 pages: 3-5 hours

You have all the tools and examples needed. The pattern is consistent across all pages!
