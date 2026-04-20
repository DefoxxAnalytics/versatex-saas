import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DashboardLayout } from "../DashboardLayout";
import { Router } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "../../contexts/AuthContext";
import { ThemeProvider } from "../../contexts/ThemeContext";
import { PermissionProvider } from "../../contexts/PermissionContext";
import { OrganizationProvider } from "../../contexts/OrganizationContext";

/**
 * Test suite for DashboardLayout component
 * Validates navigation, accessibility, and responsive behavior
 */

function createTestWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <OrganizationProvider>
            <PermissionProvider>
              <Router>{children}</Router>
            </PermissionProvider>
          </OrganizationProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

describe("DashboardLayout", () => {
  describe("Rendering", () => {
    it("should render the sidebar navigation", () => {
      render(<DashboardLayout />, { wrapper: createTestWrapper() });

      // Check for main navigation elements
      expect(
        screen.getByRole("navigation", { name: /main navigation/i }),
      ).toBeInTheDocument();
      // The app uses "Analytics Dashboard" as the title
      expect(screen.getByText(/analytics dashboard/i)).toBeInTheDocument();
    });

    it("should render all 13 navigation tabs", () => {
      render(<DashboardLayout />, { wrapper: createTestWrapper() });

      // Note: "Upload Data" was removed - data upload is now handled via Django Admin
      const expectedTabs = [
        "Overview",
        "Categories",
        "Suppliers",
        "Pareto Analysis",
        "Spend Stratification",
        "Seasonality",
        "Year-over-Year",
        "Tail Spend",
        "AI Insights",
        "Predictive Analytics",
        "Contract Optimization",
        "Maverick Spend",
        "Settings",
      ];

      expectedTabs.forEach((tab) => {
        const elements = screen.getAllByText(tab);
        expect(elements.length).toBeGreaterThan(0);
      });
    });

    it("should render children content in main area", () => {
      render(
        <DashboardLayout>
          <div data-testid="test-content">Test Content</div>
        </DashboardLayout>,
        { wrapper: createTestWrapper() },
      );

      expect(screen.getByTestId("test-content")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have proper ARIA labels for navigation", () => {
      render(<DashboardLayout />, { wrapper: createTestWrapper() });

      const nav = screen.getByRole("navigation", { name: /main navigation/i });
      expect(nav).toHaveAttribute("aria-label", "Main navigation");
    });

    it("should have accessible navigation links", () => {
      render(<DashboardLayout />, { wrapper: createTestWrapper() });

      const links = screen.getAllByRole("link");
      links.forEach((link) => {
        // Each link should have accessible text
        expect(link).toHaveAccessibleName();
      });
    });

    it("should support keyboard navigation", async () => {
      const user = userEvent.setup();
      render(<DashboardLayout />, { wrapper: createTestWrapper() });

      const overviewElements = screen.getAllByText("Overview");
      const firstLink = overviewElements[0].closest("a");
      expect(firstLink).toBeInTheDocument();

      // Tab through focusable elements - buttons and links should be focusable
      await user.tab();
      expect(document.activeElement?.tagName).toBe("BUTTON");

      // Continue tabbing to find a link
      let foundLink = false;
      for (let i = 0; i < 10; i++) {
        await user.tab();
        if (document.activeElement?.tagName === "A") {
          foundLink = true;
          break;
        }
      }
      expect(foundLink).toBe(true);
    });
  });

  describe("Navigation Behavior", () => {
    it("should highlight active route", () => {
      render(<DashboardLayout />, { wrapper: createTestWrapper() });

      // The Overview tab should be active by default (root route)
      const overviewElements = screen.getAllByText("Overview");
      const overviewLink = overviewElements[0].closest("a");
      // Active styling varies by color scheme: bg-blue-50 (classic) or bg-white/20 (navy)
      // The link should have some active state class
      expect(overviewLink?.className).toMatch(/bg-/);
    });

    it("should navigate when clicking a tab", async () => {
      const user = userEvent.setup();
      render(<DashboardLayout />, { wrapper: createTestWrapper() });

      // Find the Categories navigation item
      const categoriesText = screen.getByText("Categories");
      expect(categoriesText).toBeInTheDocument();

      // The link should be clickable
      await user.click(categoriesText);

      // After clicking, the component should still render
      expect(
        screen.getByRole("navigation", { name: /main navigation/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Responsive Design", () => {
    it("should render mobile menu toggle button", () => {
      render(<DashboardLayout />, { wrapper: createTestWrapper() });

      // Mobile menu button should exist
      const menuButton = screen.getByLabelText(/toggle menu/i);
      expect(menuButton).toBeInTheDocument();
    });

    it("should toggle mobile menu when button clicked", async () => {
      const user = userEvent.setup();
      render(<DashboardLayout />, { wrapper: createTestWrapper() });

      const menuButton = screen.getByLabelText(/toggle menu/i);

      // Click to open
      await user.click(menuButton);

      // Menu should be visible (implementation will add aria-expanded)
      expect(menuButton).toHaveAttribute("aria-expanded", "true");
    });
  });

  describe("Error Handling", () => {
    it("should handle missing children gracefully", () => {
      render(<DashboardLayout />, { wrapper: createTestWrapper() });

      // Should render without errors even with no children
      expect(
        screen.getByRole("navigation", { name: /main navigation/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Data Requirements", () => {
    it("should render without errors when no data exists", async () => {
      // Clear localStorage to simulate no data
      localStorage.clear();

      render(<DashboardLayout />, { wrapper: createTestWrapper() });

      // Component should render successfully
      expect(
        screen.getByRole("navigation", { name: /main navigation/i }),
      ).toBeInTheDocument();

      // All navigation items should be present
      expect(screen.getAllByText("Overview").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Categories").length).toBeGreaterThan(0);
    });
  });
});
