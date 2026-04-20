# Frontend Integration Guide

This guide explains how to integrate the existing React components with the Django API.

## Overview

The frontend needs to be updated to:
1. Use API calls instead of IndexedDB
2. Handle authentication state
3. Show loading states
4. Handle errors gracefully

## Already Completed

✅ API client (`src/lib/api.ts`)
✅ Authentication context (`src/contexts/AuthContext.tsx`)
✅ Axios interceptors for token refresh

## Required Changes

### 1. Update App.tsx

Replace the simple password auth with API-based auth:

```tsx
import { AuthProvider } from '@/contexts/AuthContext';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ThemeProvider defaultTheme="light">
          <TooltipProvider>
            <Toaster />
            <Router />
          </TooltipProvider>
        </ThemeProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
```

### 2. Create Login Page

```tsx
// src/pages/Login.tsx
import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigate } from 'wouter';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const [, setLocation] = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await login(username, password);
      toast.success('Logged in successfully');
      setLocation('/');
    } catch (error: any) {
      toast.error(error.response?.data?.error || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-50 via-white to-cyan-50">
      <div className="w-full max-w-md p-8 bg-white rounded-lg shadow-lg">
        <h1 className="text-2xl font-bold mb-6">Login</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
          <Input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Logging in...' : 'Login'}
          </Button>
        </form>
      </div>
    </div>
  );
}
```

### 3. Create Protected Route Component

```tsx
// src/components/ProtectedRoute.tsx
import { useAuth } from '@/contexts/AuthContext';
import { Redirect } from 'wouter';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Redirect to="/login" />;
  }

  return <>{children}</>;
}
```

### 4. Update Router

```tsx
// src/App.tsx
function Router() {
  return (
    <Switch>
      <Route path="/login" component={Login} />
      <Route path="/">
        <ProtectedRoute>
          <DashboardLayout>
            <Switch>
              <Route path="/" component={Overview} />
              <Route path="/categories" component={Categories} />
              <Route path="/suppliers" component={Suppliers} />
              {/* ... other routes */}
            </Switch>
          </DashboardLayout>
        </ProtectedRoute>
      </Route>
    </Switch>
  );
}
```

### 5. Replace IndexedDB with API Calls

Example for Overview page:

**Before (IndexedDB):**
```tsx
const { data, isLoading } = useProcurementData();
```

**After (API):**
```tsx
import { useQuery } from '@tanstack/react-query';
import { analyticsAPI } from '@/lib/api';

const { data, isLoading } = useQuery({
  queryKey: ['overview'],
  queryFn: async () => {
    const response = await analyticsAPI.getOverview();
    return response.data;
  },
});
```

### 6. Update All Page Components

For each analytics page, replace the data fetching:

**Categories Page:**
```tsx
const { data: categoryData } = useQuery({
  queryKey: ['spend-by-category'],
  queryFn: async () => {
    const response = await analyticsAPI.getSpendByCategory();
    return response.data;
  },
});
```

**Suppliers Page:**
```tsx
const { data: supplierData } = useQuery({
  queryKey: ['spend-by-supplier'],
  queryFn: async () => {
    const response = await analyticsAPI.getSpendBySupplier();
    return response.data;
  },
});
```

**Pareto Analysis:**
```tsx
const { data: paretoData } = useQuery({
  queryKey: ['pareto'],
  queryFn: async () => {
    const response = await analyticsAPI.getParetoAnalysis();
    return response.data;
  },
});
```

**Tail Spend:**
```tsx
const { data: tailData } = useQuery({
  queryKey: ['tail-spend'],
  queryFn: async () => {
    const response = await analyticsAPI.getTailSpend(20);
    return response.data;
  },
});
```

**Seasonality:**
```tsx
const { data: seasonalityData } = useQuery({
  queryKey: ['seasonality'],
  queryFn: async () => {
    const response = await analyticsAPI.getSeasonality();
    return response.data;
  },
});
```

**Year Over Year:**
```tsx
const { data: yoyData } = useQuery({
  queryKey: ['year-over-year'],
  queryFn: async () => {
    const response = await analyticsAPI.getYearOverYear();
    return response.data;
  },
});
```

### 7. Update Home Page (Upload)

```tsx
// src/pages/Home.tsx
import { procurementAPI } from '@/lib/api';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';

export default function Home() {
  const uploadMutation = useMutation({
    mutationFn: (file: File) => procurementAPI.uploadCSV(file, true),
    onSuccess: (response) => {
      toast.success(`Uploaded ${response.data.successful_rows} rows`);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Upload failed');
    },
  });

  const handleFileUpload = (file: File) => {
    uploadMutation.mutate(file);
  };

  return (
    <div>
      <input
        type="file"
        accept=".csv"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFileUpload(file);
        }}
      />
      {uploadMutation.isPending && <p>Uploading...</p>}
    </div>
  );
}
```

### 8. Update DashboardLayout

Add logout button:

```tsx
import { useAuth } from '@/contexts/AuthContext';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { logout, user } = useAuth();

  return (
    <div>
      <header>
        <span>Welcome, {user?.first_name || user?.username}</span>
        <Button onClick={logout}>Logout</Button>
      </header>
      {children}
    </div>
  );
}
```

### 9. Remove Old Files

Delete these files as they're no longer needed:
- `src/lib/db.ts` (IndexedDB)
- `src/hooks/useProcurementData.ts` (IndexedDB hooks)
- Old `src/lib/auth.ts` (simple password auth)

### 10. Update Environment Variables

Create `.env` file:
```
VITE_API_URL=http://localhost:8000/api
VITE_APP_TITLE=Analytics Dashboard
VITE_APP_LOGO=/vtx_logo2.png
```

## Testing Checklist

- [ ] Login page works
- [ ] Authentication persists on refresh
- [ ] Token refresh works automatically
- [ ] Logout clears session
- [ ] Protected routes redirect to login
- [ ] All analytics pages load data from API
- [ ] CSV upload works
- [ ] Export works
- [ ] Error messages display properly
- [ ] Loading states show correctly

## Common Issues

### CORS Errors
Make sure Django CORS settings include your frontend URL:
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
]
```

### 401 Unauthorized
Check that the token is being sent in headers:
```tsx
// Should be automatic via axios interceptor
// Check browser DevTools → Network → Headers
```

### Data Format Mismatch
The API returns slightly different data structures. Update your components to match:
```tsx
// API returns: { category: "IT", amount: 1000 }
// IndexedDB had: { Category: "IT", Spend: 1000 }
```

## Next Steps

1. Start with login page and authentication
2. Update one analytics page at a time
3. Test each page before moving to the next
4. Remove IndexedDB code once all pages work
5. Add loading skeletons for better UX
6. Add error boundaries for error handling

## Need Help?

- Check the API documentation at http://localhost:8000/api/docs
- Review the API client code in `src/lib/api.ts`
- Test API endpoints with curl or Postman first
- Check browser console for errors
