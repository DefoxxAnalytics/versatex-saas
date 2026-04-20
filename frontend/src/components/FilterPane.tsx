/**
 * FilterPane Component
 *
 * Persistent filter pane that allows users to filter procurement data.
 * Filters persist across all tabs using TanStack Query.
 *
 * Features:
 * - Date range picker
 * - Category multi-select
 * - Supplier multi-select
 * - Amount range inputs
 * - Reset filters button
 * - Active filter badges
 *
 * Security:
 * - All inputs validated and sanitized
 * - No XSS vulnerabilities
 *
 * Accessibility:
 * - Proper labels and ARIA attributes
 * - Keyboard navigation support
 */

import { useState, useMemo } from "react";
import { X, Filter, RotateCcw, Bookmark, Trash2, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { MultiSelect } from "@/components/ui/multi-select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  useFilters,
  useUpdateFilters,
  useResetFilters,
  type Filters,
} from "@/hooks/useFilters";
import { useProcurementData } from "@/hooks/useProcurementData";
import { useCategoryDetails } from "@/hooks/useAnalytics";
import { useFilterPresets, type FilterPreset } from "@/hooks/useFilterPresets";
import { toast } from "sonner";

export function FilterPane() {
  const { data: filters } = useFilters() as { data: Filters | undefined };
  const { data: procurementData = [] } = useProcurementData();
  const { data: categoryDetails = [] } = useCategoryDetails();
  const updateFilters = useUpdateFilters();
  const resetFilters = useResetFilters();
  const { presets, savePreset, deletePreset, nameExists } = useFilterPresets();

  // Local state for form inputs
  const [startDate, setStartDate] = useState(filters?.dateRange.start || "");
  const [endDate, setEndDate] = useState(filters?.dateRange.end || "");
  const [minAmount, setMinAmount] = useState(
    filters?.amountRange.min?.toString() || "",
  );
  const [maxAmount, setMaxAmount] = useState(
    filters?.amountRange.max?.toString() || "",
  );

  // Preset dialog state
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [presetName, setPresetName] = useState("");

  // Get unique suppliers, locations, years from procurement data
  const {
    uniqueSuppliers,
    uniqueLocations,
    uniqueYears,
  } = useMemo(() => {
    const suppliers = new Set<string>();
    const locations = new Set<string>();
    const years = new Set<string>();

    procurementData.forEach(
      (item: {
        supplier?: string;
        location?: string;
        date?: string;
        year?: number;
      }) => {
        if (item.supplier) suppliers.add(item.supplier);
        if (item.location) locations.add(item.location);

        if (item.year) {
          years.add(item.year.toString());
        } else if (item.date) {
          const year = new Date(item.date).getFullYear().toString();
          years.add(year);
        }
      },
    );

    return {
      uniqueSuppliers: Array.from(suppliers).sort(),
      uniqueLocations: Array.from(locations).sort(),
      uniqueYears: Array.from(years).sort((a, b) => parseInt(b) - parseInt(a)),
    };
  }, [procurementData]);

  // Get categories and subcategories from backend category details (proper hierarchy)
  const {
    uniqueCategories,
    uniqueSubcategories,
    categorySubcategoryMap,
  } = useMemo(() => {
    const categories: string[] = [];
    const subcategories = new Set<string>();
    const catSubMap = new Map<string, Set<string>>();

    categoryDetails.forEach((cat: { category: string; subcategories?: Array<{ name: string }> }) => {
      categories.push(cat.category);

      if (cat.subcategories && cat.subcategories.length > 0) {
        const subSet = new Set<string>();
        cat.subcategories.forEach((sub) => {
          subSet.add(sub.name);
          subcategories.add(sub.name);
        });
        catSubMap.set(cat.category, subSet);
      }
    });

    return {
      uniqueCategories: categories.sort(),
      uniqueSubcategories: Array.from(subcategories).sort(),
      categorySubcategoryMap: catSubMap,
    };
  }, [categoryDetails]);

  // Filter available subcategories based on selected categories
  const availableSubcategories = useMemo(() => {
    const selectedCategories = filters?.categories || [];

    // If no categories selected, show all subcategories
    if (selectedCategories.length === 0) {
      return uniqueSubcategories;
    }

    // Otherwise, show only subcategories belonging to selected categories
    const filteredSubcategories = new Set<string>();
    selectedCategories.forEach((category) => {
      const subs = categorySubcategoryMap.get(category);
      if (subs) {
        subs.forEach((sub) => filteredSubcategories.add(sub));
      }
    });

    return Array.from(filteredSubcategories).sort();
  }, [filters?.categories, categorySubcategoryMap, uniqueSubcategories]);

  // Handle category change with automatic subcategory cleanup
  const handleCategoryChange = (selected: string[]) => {
    // First, update categories
    updateFilters.mutate({ categories: selected });

    // If categories were selected, check if current subcategories are still valid
    if (selected.length > 0 && filters?.subcategories && filters.subcategories.length > 0) {
      // Get all valid subcategories for the new category selection
      const validSubcategories = new Set<string>();
      selected.forEach((category) => {
        const subs = categorySubcategoryMap.get(category);
        if (subs) {
          subs.forEach((sub) => validSubcategories.add(sub));
        }
      });

      // Filter out any subcategories that are no longer valid
      const validSelectedSubcategories = filters.subcategories.filter((sub) =>
        validSubcategories.has(sub)
      );

      // If any subcategories were removed, update the filter
      if (validSelectedSubcategories.length !== filters.subcategories.length) {
        updateFilters.mutate({ subcategories: validSelectedSubcategories });
      }
    }
  };

  // Count active filters
  const activeFilterCount = useMemo(() => {
    if (!filters) return 0;
    let count = 0;
    if (filters.dateRange.start || filters.dateRange.end) count++;
    if (filters.categories.length > 0) count++;
    if (filters.subcategories.length > 0) count++;
    if (filters.suppliers.length > 0) count++;
    if (filters.locations.length > 0) count++;
    if (filters.years.length > 0) count++;
    if (filters.amountRange.min !== null || filters.amountRange.max !== null)
      count++;
    return count;
  }, [filters]);

  // Handle date range update
  const handleDateRangeChange = () => {
    updateFilters.mutate({
      dateRange: {
        start: startDate || null,
        end: endDate || null,
      },
    });
  };

  // Handle category toggle
  const toggleCategory = (category: string) => {
    const current = filters?.categories || [];
    const updated = current.includes(category)
      ? current.filter((c) => c !== category)
      : [...current, category];

    updateFilters.mutate({ categories: updated });
  };

  // Handle subcategory toggle
  const toggleSubcategory = (subcategory: string) => {
    const current = filters?.subcategories || [];
    const updated = current.includes(subcategory)
      ? current.filter((sc) => sc !== subcategory)
      : [...current, subcategory];

    updateFilters.mutate({ subcategories: updated });
  };

  // Handle supplier toggle
  const toggleSupplier = (supplier: string) => {
    const current = filters?.suppliers || [];
    const updated = current.includes(supplier)
      ? current.filter((s) => s !== supplier)
      : [...current, supplier];

    updateFilters.mutate({ suppliers: updated });
  };

  // Handle location toggle
  const toggleLocation = (location: string) => {
    const current = filters?.locations || [];
    const updated = current.includes(location)
      ? current.filter((l) => l !== location)
      : [...current, location];

    updateFilters.mutate({ locations: updated });
  };

  // Handle amount range update
  const handleAmountRangeChange = () => {
    updateFilters.mutate({
      amountRange: {
        min: minAmount ? parseFloat(minAmount) : null,
        max: maxAmount ? parseFloat(maxAmount) : null,
      },
    });
  };

  // Handle reset
  const handleReset = () => {
    resetFilters.mutate();
    setStartDate("");
    setEndDate("");
    setMinAmount("");
    setMaxAmount("");
  };

  // Handle save preset
  const handleSavePreset = () => {
    if (!presetName.trim()) {
      toast.error("Please enter a preset name");
      return;
    }
    if (nameExists(presetName)) {
      toast.error("A preset with this name already exists");
      return;
    }
    if (!filters) return;

    savePreset(presetName.trim(), filters);
    toast.success(`Preset "${presetName}" saved`);
    setPresetName("");
    setSaveDialogOpen(false);
  };

  // Handle apply preset
  const handleApplyPreset = (preset: FilterPreset) => {
    // Update all filters from preset
    updateFilters.mutate(preset.filters);

    // Update local state
    setStartDate(preset.filters.dateRange.start || "");
    setEndDate(preset.filters.dateRange.end || "");
    setMinAmount(preset.filters.amountRange.min?.toString() || "");
    setMaxAmount(preset.filters.amountRange.max?.toString() || "");

    toast.success(`Applied preset "${preset.name}"`);
  };

  // Handle delete preset
  const handleDeletePreset = (preset: FilterPreset, e: React.MouseEvent) => {
    e.stopPropagation();
    deletePreset(preset.id);
    toast.success(`Deleted preset "${preset.name}"`);
  };

  if (!filters) return null;

  return (
    <Card className="h-full">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div className="flex items-center gap-2">
          <Filter className="h-5 w-5" />
          <CardTitle className="text-lg font-semibold">Filters</CardTitle>
          {activeFilterCount > 0 && (
            <Badge variant="secondary" className="ml-2">
              {activeFilterCount}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-1">
          {/* Presets Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2"
                aria-label="Filter presets"
              >
                <Bookmark className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuItem onClick={() => setSaveDialogOpen(true)}>
                <Bookmark className="h-4 w-4 mr-2" />
                Save Current Filters
              </DropdownMenuItem>
              {presets.length > 0 && (
                <>
                  <DropdownMenuSeparator />
                  {presets.map((preset) => (
                    <DropdownMenuItem
                      key={preset.id}
                      onClick={() => handleApplyPreset(preset)}
                      className="flex items-center justify-between group"
                    >
                      <span className="truncate">{preset.name}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"
                        onClick={(e) => handleDeletePreset(preset, e)}
                      >
                        <Trash2 className="h-3 w-3 text-destructive" />
                      </Button>
                    </DropdownMenuItem>
                  ))}
                </>
              )}
              {presets.length === 0 && (
                <div className="text-xs text-muted-foreground text-center py-2">
                  No saved presets
                </div>
              )}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Reset Button */}
          {activeFilterCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleReset}
              className="h-8 px-2"
              aria-label="Reset all filters"
            >
              <RotateCcw className="h-4 w-4 mr-1" />
              Reset
            </Button>
          )}
        </div>
      </CardHeader>

      {/* Save Preset Dialog */}
      <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Save Filter Preset</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="preset-name">Preset Name</Label>
              <Input
                id="preset-name"
                placeholder="e.g., Q1 2024 Analysis"
                value={presetName}
                onChange={(e) => setPresetName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleSavePreset();
                  }
                }}
              />
            </div>
            <div className="text-sm text-muted-foreground">
              <p>This will save:</p>
              <ul className="list-disc list-inside mt-1 space-y-0.5">
                {filters.dateRange.start && (
                  <li>
                    Date: {filters.dateRange.start} -{" "}
                    {filters.dateRange.end || "Now"}
                  </li>
                )}
                {filters.categories.length > 0 && (
                  <li>{filters.categories.length} categories</li>
                )}
                {filters.suppliers.length > 0 && (
                  <li>{filters.suppliers.length} suppliers</li>
                )}
                {filters.locations.length > 0 && (
                  <li>{filters.locations.length} locations</li>
                )}
                {(filters.amountRange.min !== null ||
                  filters.amountRange.max !== null) && (
                  <li>Amount range filter</li>
                )}
                {activeFilterCount === 0 && (
                  <li className="text-amber-600">No active filters</li>
                )}
              </ul>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSaveDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSavePreset}>
              <Check className="h-4 w-4 mr-2" />
              Save Preset
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <CardContent className="space-y-6">
        {/* Date Range Filter */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">Date Range</Label>

          {/* Quick Date Presets */}
          <div className="flex flex-wrap gap-1.5">
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs px-2"
              onClick={() => {
                const today = new Date();
                const start = new Date(today);
                start.setDate(start.getDate() - 7);
                const startStr = start.toISOString().split("T")[0];
                const endStr = today.toISOString().split("T")[0];
                setStartDate(startStr);
                setEndDate(endStr);
                updateFilters.mutate({
                  dateRange: { start: startStr, end: endStr },
                });
              }}
            >
              Last 7 days
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs px-2"
              onClick={() => {
                const today = new Date();
                const start = new Date(today);
                start.setDate(start.getDate() - 30);
                const startStr = start.toISOString().split("T")[0];
                const endStr = today.toISOString().split("T")[0];
                setStartDate(startStr);
                setEndDate(endStr);
                updateFilters.mutate({
                  dateRange: { start: startStr, end: endStr },
                });
              }}
            >
              Last 30 days
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs px-2"
              onClick={() => {
                const today = new Date();
                const start = new Date(today);
                start.setDate(start.getDate() - 90);
                const startStr = start.toISOString().split("T")[0];
                const endStr = today.toISOString().split("T")[0];
                setStartDate(startStr);
                setEndDate(endStr);
                updateFilters.mutate({
                  dateRange: { start: startStr, end: endStr },
                });
              }}
            >
              Last 90 days
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs px-2"
              onClick={() => {
                const year = new Date().getFullYear();
                const startStr = `${year}-01-01`;
                setStartDate(startStr);
                setEndDate("");
                updateFilters.mutate({
                  dateRange: { start: startStr, end: null },
                });
              }}
            >
              This Year
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs px-2"
              onClick={() => {
                const year = new Date().getFullYear() - 1;
                const startStr = `${year}-01-01`;
                const endStr = `${year}-12-31`;
                setStartDate(startStr);
                setEndDate(endStr);
                updateFilters.mutate({
                  dateRange: { start: startStr, end: endStr },
                });
              }}
            >
              Last Year
            </Button>
          </div>

          <div className="space-y-2">
            <div>
              <Label htmlFor="start-date" className="text-xs text-gray-600">
                Start Date
              </Label>
              <Input
                id="start-date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                onBlur={handleDateRangeChange}
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="end-date" className="text-xs text-gray-600">
                End Date
              </Label>
              <Input
                id="end-date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                onBlur={handleDateRangeChange}
                className="mt-1"
              />
            </div>
          </div>
          {(filters.dateRange.start || filters.dateRange.end) && (
            <div className="flex flex-wrap gap-2">
              {filters.dateRange.start && (
                <Badge variant="secondary" className="text-xs">
                  From: {filters.dateRange.start}
                  <X
                    className="h-3 w-3 ml-1 cursor-pointer"
                    onClick={() => {
                      setStartDate("");
                      updateFilters.mutate({
                        dateRange: { ...filters.dateRange, start: null },
                      });
                    }}
                  />
                </Badge>
              )}
              {filters.dateRange.end && (
                <Badge variant="secondary" className="text-xs">
                  To: {filters.dateRange.end}
                  <X
                    className="h-3 w-3 ml-1 cursor-pointer"
                    onClick={() => {
                      setEndDate("");
                      updateFilters.mutate({
                        dateRange: { ...filters.dateRange, end: null },
                      });
                    }}
                  />
                </Badge>
              )}
            </div>
          )}
        </div>

        {/* Category Filter */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">Categories</Label>
          <MultiSelect
            options={uniqueCategories}
            selected={filters.categories}
            onChange={handleCategoryChange}
            placeholder="Select categories..."
            emptyMessage="No categories available"
          />
        </div>

        {/* Subcategory Filter */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">
            Subcategories
            {filters.categories.length > 0 && (
              <span className="text-xs text-muted-foreground ml-1">
                (filtered by {filters.categories.length} {filters.categories.length === 1 ? "category" : "categories"})
              </span>
            )}
          </Label>
          <MultiSelect
            options={availableSubcategories}
            selected={filters.subcategories}
            onChange={(selected) =>
              updateFilters.mutate({ subcategories: selected })
            }
            placeholder={
              filters.categories.length > 0
                ? "Select subcategories..."
                : "Select categories first or choose any..."
            }
            emptyMessage={
              filters.categories.length > 0
                ? "No subcategories for selected categories"
                : "No subcategories available"
            }
          />
        </div>

        {/* Supplier Filter */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">Suppliers</Label>
          <MultiSelect
            options={uniqueSuppliers}
            selected={filters.suppliers}
            onChange={(selected) =>
              updateFilters.mutate({ suppliers: selected })
            }
            placeholder="Select suppliers..."
            emptyMessage="No suppliers available"
          />
        </div>

        {/* Location Filter */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">Locations</Label>
          <MultiSelect
            options={uniqueLocations}
            selected={filters.locations}
            onChange={(selected) =>
              updateFilters.mutate({ locations: selected })
            }
            placeholder="Select locations..."
            emptyMessage="No locations available"
          />
        </div>

        {/* Year Filter */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">Years</Label>
          <MultiSelect
            options={uniqueYears}
            selected={filters.years}
            onChange={(selected) => updateFilters.mutate({ years: selected })}
            placeholder="Select years..."
            emptyMessage="No years available"
          />
        </div>

        {/* Amount Range Filter */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">Amount Range</Label>
          <div className="space-y-2">
            <div>
              <Label htmlFor="min-amount" className="text-xs text-gray-600">
                Minimum
              </Label>
              <Input
                id="min-amount"
                type="number"
                placeholder="0"
                value={minAmount}
                onChange={(e) => setMinAmount(e.target.value)}
                onBlur={handleAmountRangeChange}
                className="mt-1"
                min="0"
                step="0.01"
              />
            </div>
            <div>
              <Label htmlFor="max-amount" className="text-xs text-gray-600">
                Maximum
              </Label>
              <Input
                id="max-amount"
                type="number"
                placeholder="No limit"
                value={maxAmount}
                onChange={(e) => setMaxAmount(e.target.value)}
                onBlur={handleAmountRangeChange}
                className="mt-1"
                min="0"
                step="0.01"
              />
            </div>
          </div>
          {(filters.amountRange.min !== null ||
            filters.amountRange.max !== null) && (
            <div className="flex flex-wrap gap-2">
              {filters.amountRange.min !== null && (
                <Badge variant="secondary" className="text-xs">
                  Min: ${filters.amountRange.min.toLocaleString()}
                  <X
                    className="h-3 w-3 ml-1 cursor-pointer"
                    onClick={() => {
                      setMinAmount("");
                      updateFilters.mutate({
                        amountRange: { ...filters.amountRange, min: null },
                      });
                    }}
                  />
                </Badge>
              )}
              {filters.amountRange.max !== null && (
                <Badge variant="secondary" className="text-xs">
                  Max: ${filters.amountRange.max.toLocaleString()}
                  <X
                    className="h-3 w-3 ml-1 cursor-pointer"
                    onClick={() => {
                      setMaxAmount("");
                      updateFilters.mutate({
                        amountRange: { ...filters.amountRange, max: null },
                      });
                    }}
                  />
                </Badge>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
