import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/NotFound";
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DashboardLayout } from "./components/DashboardLayout";
import { lazy, Suspense } from "react";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { PermissionProvider } from "./contexts/PermissionContext";
import { OrganizationProvider } from "./contexts/OrganizationContext";
import { Redirect } from "wouter";

// Lazy load pages for code splitting and performance
const Login = lazy(() => import("./pages/Login"));
const Overview = lazy(() => import("./pages/Overview"));
const CategoriesPage = lazy(() => import("./pages/Categories"));
const SuppliersPage = lazy(() => import("./pages/Suppliers"));
const ParetoPage = lazy(() => import("./pages/ParetoAnalysis"));
const StratificationPage = lazy(() => import("./pages/SpendStratification"));
const SeasonalityPage = lazy(() => import("./pages/Seasonality"));
const YoYPage = lazy(() => import("./pages/YearOverYear"));
const TailSpendPage = lazy(() => import("./pages/TailSpend"));
const AIInsightsPage = lazy(() => import("./pages/ai-insights"));
const PredictivePage = lazy(() => import("./pages/predictive"));
const ContractsPage = lazy(() => import("./pages/contracts"));
const MaverickPage = lazy(() => import("./pages/maverick"));
const ReportsPage = lazy(() => import("./pages/reports"));
const SettingsPage = lazy(() => import("./pages/Settings"));

// P2P Analytics Pages
const P2PCyclePage = lazy(() => import("./pages/p2p/P2PCycle"));
const MatchingPage = lazy(() => import("./pages/p2p/Matching"));
const InvoiceAgingPage = lazy(() => import("./pages/p2p/InvoiceAging"));
const RequisitionsPage = lazy(() => import("./pages/p2p/Requisitions"));
const PurchaseOrdersPage = lazy(() => import("./pages/p2p/PurchaseOrders"));
const SupplierPaymentsPage = lazy(() => import("./pages/p2p/SupplierPayments"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

/**
 * Loading fallback component for lazy-loaded pages
 * Provides visual feedback during code splitting
 */
function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="flex flex-col items-center gap-3">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="text-sm text-gray-600">Loading...</p>
      </div>
    </div>
  );
}

/**
 * Protected route wrapper - redirects to login if not authenticated
 */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuth } = useAuth();

  if (!isAuth) {
    return <Redirect to="/login" />;
  }

  return <>{children}</>;
}

/**
 * Main router component with all application routes
 * Uses lazy loading for optimal performance
 */
function Router() {
  return (
    <Switch>
      {/* Login route - public */}
      <Route path="/login">
        <Suspense fallback={<PageLoader />}>
          <Login />
        </Suspense>
      </Route>
      {/* Overview route - dashboard (protected) */}
      <Route path="/">
        <ProtectedRoute>
          <DashboardLayout>
            <Suspense fallback={<PageLoader />}>
              <Overview />
            </Suspense>
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      {/* All other routes use DashboardLayout (protected) */}
      <Route path="/categories">
        <ProtectedRoute>
          <DashboardLayout>
            <Suspense fallback={<PageLoader />}>
              <CategoriesPage />
            </Suspense>
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      <Route path="/suppliers">
        <ProtectedRoute>
          <DashboardLayout>
            <Suspense fallback={<PageLoader />}>
              <SuppliersPage />
            </Suspense>
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      <Route path="/pareto">
        <ProtectedRoute>
          <DashboardLayout>
            <Suspense fallback={<PageLoader />}>
              <ParetoPage />
            </Suspense>
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      <Route path="/stratification">
        <ProtectedRoute>
          <DashboardLayout>
            <Suspense fallback={<PageLoader />}>
              <StratificationPage />
            </Suspense>
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      <Route path="/seasonality">
        <ProtectedRoute>
          <DashboardLayout>
            <Suspense fallback={<PageLoader />}>
              <SeasonalityPage />
            </Suspense>
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      <Route path="/yoy">
        <ProtectedRoute>
          <DashboardLayout>
            <Suspense fallback={<PageLoader />}>
              <YoYPage />
            </Suspense>
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      <Route path="/tail-spend">
        <ProtectedRoute>
          <DashboardLayout>
            <Suspense fallback={<PageLoader />}>
              <TailSpendPage />
            </Suspense>
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      <Route path="/ai-insights">
        <ProtectedRoute>
          <DashboardLayout>
            <Suspense fallback={<PageLoader />}>
              <AIInsightsPage />
            </Suspense>
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      <Route path="/predictive">
        <ProtectedRoute>
          <DashboardLayout>
            <Suspense fallback={<PageLoader />}>
              <PredictivePage />
            </Suspense>
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      <Route path="/contracts">
        <ProtectedRoute>
          <DashboardLayout>
            <Suspense fallback={<PageLoader />}>
              <ContractsPage />
            </Suspense>
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      <Route path="/maverick">
        <ProtectedRoute>
          <DashboardLayout>
            <Suspense fallback={<PageLoader />}>
              <MaverickPage />
            </Suspense>
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      <Route path="/reports">
        <ProtectedRoute>
          <DashboardLayout>
            <Suspense fallback={<PageLoader />}>
              <ReportsPage />
            </Suspense>
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      <Route path="/settings">
        <ProtectedRoute>
          <DashboardLayout>
            <Suspense fallback={<PageLoader />}>
              <SettingsPage />
            </Suspense>
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      {/* P2P Analytics Routes */}
      <Route path="/p2p-cycle">
        <ProtectedRoute>
          <DashboardLayout>
            <Suspense fallback={<PageLoader />}>
              <P2PCyclePage />
            </Suspense>
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      <Route path="/matching">
        <ProtectedRoute>
          <DashboardLayout>
            <Suspense fallback={<PageLoader />}>
              <MatchingPage />
            </Suspense>
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      <Route path="/invoice-aging">
        <ProtectedRoute>
          <DashboardLayout>
            <Suspense fallback={<PageLoader />}>
              <InvoiceAgingPage />
            </Suspense>
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      <Route path="/requisitions">
        <ProtectedRoute>
          <DashboardLayout>
            <Suspense fallback={<PageLoader />}>
              <RequisitionsPage />
            </Suspense>
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      <Route path="/purchase-orders">
        <ProtectedRoute>
          <DashboardLayout>
            <Suspense fallback={<PageLoader />}>
              <PurchaseOrdersPage />
            </Suspense>
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      <Route path="/supplier-payments">
        <ProtectedRoute>
          <DashboardLayout>
            <Suspense fallback={<PageLoader />}>
              <SupplierPaymentsPage />
            </Suspense>
          </DashboardLayout>
        </ProtectedRoute>
      </Route>

      {/* 404 fallback */}
      <Route path="/404" component={NotFound} />
      <Route component={NotFound} />
    </Switch>
  );
}

/**
 * Root application component
 * Sets up all providers and global configuration
 */
function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider defaultTheme="light" switchable>
          <AuthProvider>
            <PermissionProvider>
              <OrganizationProvider>
                <TooltipProvider>
                  <Toaster />
                  <Router />
                </TooltipProvider>
              </OrganizationProvider>
            </PermissionProvider>
          </AuthProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
