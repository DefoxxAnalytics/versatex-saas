import * as React from "react";
import { Check, ChevronDown, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";

export interface MultiSelectProps {
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
  placeholder?: string;
  emptyMessage?: string;
  className?: string;
}

export function MultiSelect({
  options,
  selected,
  onChange,
  placeholder = "Select items...",
  emptyMessage = "No items found.",
  className,
}: MultiSelectProps) {
  const [open, setOpen] = React.useState(false);

  const handleSelect = (value: string) => {
    const newSelected = selected.includes(value)
      ? selected.filter((item) => item !== value)
      : [...selected, value];
    onChange(newSelected);
  };

  const handleRemove = (value: string) => {
    onChange(selected.filter((item) => item !== value));
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={cn(
            "w-full justify-between h-auto min-h-[2.5rem] px-3 py-2",
            className,
          )}
        >
          <div className="flex flex-wrap gap-1 flex-1">
            {selected.length > 0 ? (
              selected.map((item) => (
                <Badge
                  key={item}
                  variant="secondary"
                  className="mr-1 text-xs"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemove(item);
                  }}
                >
                  {item}
                  <X className="ml-1 h-3 w-3 cursor-pointer" />
                </Badge>
              ))
            ) : (
              <span className="text-muted-foreground text-sm">
                {placeholder}
              </span>
            )}
          </div>
          <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-full p-0" align="start">
        <Command>
          <CommandInput placeholder="Search..." className="h-9" />
          <CommandEmpty>{emptyMessage}</CommandEmpty>
          <CommandGroup className="max-h-64 overflow-auto">
            {options.map((option) => (
              <CommandItem
                key={option}
                onSelect={() => handleSelect(option)}
                className="cursor-pointer"
              >
                <div
                  className={cn(
                    "mr-2 flex h-4 w-4 items-center justify-center rounded-sm border border-primary",
                    selected.includes(option)
                      ? "bg-primary text-primary-foreground"
                      : "opacity-50 [&_svg]:invisible",
                  )}
                >
                  <Check className="h-4 w-4" />
                </div>
                <span>{option}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
