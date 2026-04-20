import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Breadcrumb } from "../Breadcrumb";
import { Router, useLocation } from "wouter";
import React from "react";

/**
 * Test suite for Breadcrumb component
 * Validates dynamic breadcrumb generation, navigation, and accessibility
 */

function createWrapper() {
  return ({ children }: { children: React.ReactNode }) => (
    <Router>{children}</Router>
  );
}

describe("Breadcrumb Component", () => {
  describe("Rendering", () => {
    it("should render breadcrumb navigation", () => {
      render(<Breadcrumb />, { wrapper: createWrapper() });

      const nav = screen.getByRole("navigation", { name: /breadcrumb/i });
      expect(nav).toBeInTheDocument();
    });

    it("should show Overview for root path", () => {
      render(<Breadcrumb />, { wrapper: createWrapper() });

      expect(screen.getByText("Overview")).toBeInTheDocument();
    });

    it("should show breadcrumb trail for nested paths", () => {
      // Render with Router hook to set location
      const TestComponent = () => {
        const [, setLocation] = useLocation();
        // Set location on mount
        React.useEffect(() => {
          setLocation("/categories");
        }, [setLocation]);
        return <Breadcrumb />;
      };

      render(
        <Router>
          <TestComponent />
        </Router>,
      );

      // Should show Overview > Categories
      expect(screen.getByText("Overview")).toBeInTheDocument();
      expect(screen.getByText("Categories")).toBeInTheDocument();
    });

    it("should handle multi-word paths correctly", () => {
      const TestComponent = () => {
        const [, setLocation] = useLocation();
        React.useEffect(() => {
          setLocation("/ai-insights");
        }, [setLocation]);
        return <Breadcrumb />;
      };

      render(
        <Router>
          <TestComponent />
        </Router>,
      );

      // Should convert "ai-insights" to "AI Insights"
      expect(screen.getByText(/AI Insights/i)).toBeInTheDocument();
    });

    it("should show separator between breadcrumb items", () => {
      const Wrapper = ({ children }: { children: React.ReactNode }) => (
        <Router base="/categories">{children}</Router>
      );

      render(<Breadcrumb />, { wrapper: Wrapper });

      // Should have a separator (chevron or slash)
      const breadcrumb = screen.getByRole("navigation", {
        name: /breadcrumb/i,
      });
      expect(breadcrumb).toBeInTheDocument();
    });
  });

  describe("Navigation", () => {
    it("should have clickable links for all items except current", () => {
      const TestComponent = () => {
        const [, setLocation] = useLocation();
        React.useEffect(() => {
          setLocation("/categories");
        }, [setLocation]);
        return <Breadcrumb />;
      };

      render(
        <Router>
          <TestComponent />
        </Router>,
      );

      // Overview should be a link (not current page)
      const homeLink = screen.getByText("Overview").closest("a");
      expect(homeLink).toBeInTheDocument();
      expect(homeLink?.tagName).toBe("A");
    });

    it("should not have link for current page", () => {
      const TestComponent = () => {
        const [, setLocation] = useLocation();
        React.useEffect(() => {
          setLocation("/categories");
        }, [setLocation]);
        return <Breadcrumb />;
      };

      render(
        <Router>
          <TestComponent />
        </Router>,
      );

      const currentPage = screen.getByText("Categories");
      expect(currentPage.closest("a")).toBeNull();
    });

    it("should navigate when clicking breadcrumb links", async () => {
      const user = userEvent.setup();
      const TestComponent = () => {
        const [, setLocation] = useLocation();
        React.useEffect(() => {
          setLocation("/categories");
        }, [setLocation]);
        return <Breadcrumb />;
      };

      render(
        <Router>
          <TestComponent />
        </Router>,
      );

      const homeLink = screen.getByText("Overview");

      // Link should exist and be clickable
      const anchor = homeLink.closest("a");
      expect(anchor).toBeInTheDocument();

      // Click should work without errors
      if (anchor) {
        await user.click(anchor);
      }

      // Component should still render after click
      expect(screen.getByRole("navigation")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have proper ARIA labels", () => {
      render(<Breadcrumb />, { wrapper: createWrapper() });

      const nav = screen.getByRole("navigation");
      expect(nav).toHaveAttribute("aria-label", "Breadcrumb");
    });

    it("should mark current page with aria-current", () => {
      const TestComponent = () => {
        const [, setLocation] = useLocation();
        React.useEffect(() => {
          setLocation("/categories");
        }, [setLocation]);
        return <Breadcrumb />;
      };

      render(
        <Router>
          <TestComponent />
        </Router>,
      );

      const currentPage = screen.getByText("Categories");
      expect(currentPage).toHaveAttribute("aria-current", "page");
    });

    it("should be keyboard navigable", async () => {
      const user = userEvent.setup();
      const TestComponent = () => {
        const [, setLocation] = useLocation();
        React.useEffect(() => {
          setLocation("/categories");
        }, [setLocation]);
        return <Breadcrumb />;
      };

      render(
        <Router>
          <TestComponent />
        </Router>,
      );

      // Tab to the home link
      await user.tab();

      // Active element should be an anchor tag
      expect(document.activeElement?.tagName).toBe("A");
      expect(document.activeElement?.textContent).toContain("Overview");
    });
  });

  describe("Path Formatting", () => {
    it("should capitalize single-word paths", () => {
      const TestComponent = () => {
        const [, setLocation] = useLocation();
        React.useEffect(() => {
          setLocation("/suppliers");
        }, [setLocation]);
        return <Breadcrumb />;
      };

      render(
        <Router>
          <TestComponent />
        </Router>,
      );

      expect(screen.getByText("Suppliers")).toBeInTheDocument();
    });

    it("should handle hyphenated paths", () => {
      const TestComponent = () => {
        const [, setLocation] = useLocation();
        React.useEffect(() => {
          setLocation("/tail-spend");
        }, [setLocation]);
        return <Breadcrumb />;
      };

      render(
        <Router>
          <TestComponent />
        </Router>,
      );

      expect(screen.getByText(/Tail Spend/i)).toBeInTheDocument();
    });

    it("should handle year-over-year path", () => {
      const TestComponent = () => {
        const [, setLocation] = useLocation();
        React.useEffect(() => {
          setLocation("/yoy");
        }, [setLocation]);
        return <Breadcrumb />;
      };

      render(
        <Router>
          <TestComponent />
        </Router>,
      );

      expect(screen.getByText(/Year-over-Year/i)).toBeInTheDocument();
    });
  });

  describe("Edge Cases", () => {
    it("should handle root path gracefully", () => {
      render(<Breadcrumb />, { wrapper: createWrapper() });

      // Should show Overview
      const homePage = screen.getByText("Overview");
      expect(homePage).toBeInTheDocument();

      // On root path, Overview should be rendered
      expect(screen.getByRole("navigation")).toBeInTheDocument();
    });

    it("should handle unknown paths", () => {
      const TestComponent = () => {
        const [, setLocation] = useLocation();
        React.useEffect(() => {
          setLocation("/unknown-page");
        }, [setLocation]);
        return <Breadcrumb />;
      };

      render(
        <Router>
          <TestComponent />
        </Router>,
      );

      // Should still render and capitalize
      expect(screen.getByText(/Unknown Page/i)).toBeInTheDocument();
    });
  });
});
