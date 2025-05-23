import {
  DrawerActionTrigger,
  DrawerBackdrop,
  DrawerBody,
  DrawerCloseTrigger,
  DrawerContent,
  DrawerFooter,
  DrawerHeader,
  DrawerRoot,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer";
import type React from "react";

import { NonPowerUserButtons } from "@/components/Common/Filtering/NonPowerUserFilters";
import { PowerUserButtons } from "@/components/Common/Filtering/PowerUserFilters";
import { useIsMobile } from "@/hooks/useIsMobile";
import { Box, Button, Text } from "@chakra-ui/react";
import { useState } from "react";
import { BsFunnel } from "react-icons/bs";
import type { GroupByOption } from "./GroupingConfig";

export function FilterGroup({
  groupingOptionsChoices,
  setShowDeposits,
  showDeposits,
}: {
  setShowDeposits: React.Dispatch<React.SetStateAction<boolean>>;
  showDeposits: boolean;
  groupingOptionsChoices: { [key in GroupByOption]: string[] } | undefined;
}) {
  const isMobile = useIsMobile();

  const [open, setOpen] = useState(false);

  if (isMobile) {
    return (
      <DrawerRoot
        open={open}
        onOpenChange={(e) => setOpen(e.open)}
        placement={"bottom"}
      >
        <DrawerBackdrop />
        <DrawerTrigger asChild>
          <Button variant="outline" size="sm">
            <Text>Adjust Filters</Text>
            <BsFunnel />
          </Button>
        </DrawerTrigger>
        <DrawerContent>
          <DrawerHeader>
            <DrawerTitle />
          </DrawerHeader>
          <DrawerBody>
            <InnerFilterGroup
              groupingOptionsChoices={groupingOptionsChoices}
              setShowDeposits={setShowDeposits}
              showDeposits={showDeposits}
            />
          </DrawerBody>
          <DrawerFooter>
            <DrawerActionTrigger asChild>
              <Button variant="outline">Close</Button>
            </DrawerActionTrigger>
          </DrawerFooter>
          <DrawerCloseTrigger />
        </DrawerContent>
      </DrawerRoot>
    );
  }

  return (
    <InnerFilterGroup
      groupingOptionsChoices={groupingOptionsChoices}
      setShowDeposits={setShowDeposits}
      showDeposits={showDeposits}
    />
  );
}

function InnerFilterGroup({
  groupingOptionsChoices,
  setShowDeposits,
  showDeposits,
}: {
  setShowDeposits: React.Dispatch<React.SetStateAction<boolean>>;
  showDeposits: boolean;
  groupingOptionsChoices: { [Key in GroupByOption]: string[] } | undefined;
}) {
  return (
    <div
      style={{
        backgroundColor: "background",
        zIndex: 100,
        minHeight: "150px",
        padding: "1px 0",
        marginBottom: "10px",
      }}
    >
      <div>
        <Box borderWidth={1} borderRadius="md" p={2} mr={2}>
          <NonPowerUserButtons />
          <PowerUserButtons
            groupingOptionsChoices={groupingOptionsChoices}
            setShowDeposits={setShowDeposits}
            showDeposits={showDeposits}
          />
        </Box>
      </div>
    </div>
  );
}
