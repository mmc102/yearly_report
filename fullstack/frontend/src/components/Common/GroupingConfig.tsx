import { useCheckboxGroup, Menu, Button, Portal } from "@chakra-ui/react";
import { FiCheck } from "react-icons/fi";
import { Text } from "@chakra-ui/react";
import { AddIcon } from "@chakra-ui/icons";
import { FilterData_Input, FilterEntries } from "@/client";
import { useFilters } from "@/contexts/FilterContext";
import { useEffect } from "react";

export enum GroupByOption {
  category = "category",
  month = "month",
  year = "year",
  account = "account",
  budget = "budget",
}

const availableOptions: GroupByOption[] = [
  GroupByOption.category,
  GroupByOption.year,
  GroupByOption.month,
  GroupByOption.account,
  GroupByOption.budget,
];

interface GroupingConfigProps {
  groupingOptions: GroupByOption[];
  showBudgets: boolean;
}

export function GroupingConfig({
  groupingOptions,
  showBudgets,
}: GroupingConfigProps) {

  const { setCurrentFilter, currentFilter, initializeDefaultFilter } = useFilters();

  useEffect(() => {
    if (!currentFilter) {
      initializeDefaultFilter();
    }
  }, [currentFilter, initializeDefaultFilter]);

  const handleToggleOption = (option: GroupByOption) => {
    setCurrentFilter((prev: FilterData_Input | null) => {
      if (!prev) return prev;
      
      const newLookup = { ...prev.lookup };
      
      if (newLookup[option]) {
        const { [option]: removed, ...rest } = newLookup;
        return { ...prev, lookup: rest };
      } else {
        // Add the option with the next available index
        const maxIndex = Object.values(newLookup).reduce(
          (max, entry) => Math.max(max, (entry as FilterEntries).index), -1
        ) as number;
        
        const calculatedLookup = {
          ...prev,
          lookup: {
            ...newLookup,
            [option]: {
              all: true,
              visible: true,
              specifics: [],
              index: maxIndex + 1
            }
          }
        };
        return calculatedLookup;
      }
    });
  };

  const filteredOptions = showBudgets
    ? availableOptions
    : availableOptions.filter((option) => option !== GroupByOption.budget);

  const group = useCheckboxGroup({ value: groupingOptions });

  return (
    <Menu.Root key="grouping-config" onSelect={(value)=>handleToggleOption(value.value as GroupByOption)}>
      <Menu.Trigger asChild>
        <Button  variant="plain" size="sm">
          <Text textDecoration={'underline'}>Add another filter group</Text> <AddIcon/>
        </Button>
      </Menu.Trigger>
      <Portal>
        <Menu.Positioner>
          <Menu.Content zIndex={10000}>
            <Menu.ItemGroup>
              {filteredOptions.map((option, index) => (
                  <Menu.CheckboxItem
                    key={index.toString()}
                    value={option}
                    disabled={group.isChecked(option)}
                    checked={group.isChecked(option)}
                    onCheckedChange={() => group.toggleValue(option)}
                  >
                    {option.charAt(0).toUpperCase() + option.slice(1)}
                    {group.isChecked(option) && <FiCheck />}
                  </Menu.CheckboxItem>
              ))}
            </Menu.ItemGroup>
          </Menu.Content>
        </Menu.Positioner>
      </Portal>
    </Menu.Root>
  );

}
