import type { TransactionSourceGroup } from "@/client";
import { Box, HStack, Tag } from "@chakra-ui/react";
import type React from "react";

export function TransactionSourceSelector({
  allTransactionSources,
  activeTransactionSource,
  setActiveTransactionSource,
}: {
  allTransactionSources: TransactionSourceGroup[];
  activeTransactionSource: TransactionSourceGroup;
  setActiveTransactionSource: React.Dispatch<
    React.SetStateAction<TransactionSourceGroup | null>
  >;
}) {
  return (
    <Box borderWidth={1} borderRadius="md" borderColor="green.500" p={2}>
      <HStack>
        {allTransactionSources.map((sourceGroup, index) => {
          const isActive =
            activeTransactionSource.transaction_source_id ===
            sourceGroup.transaction_source_id;
          return (
            <Tag.Root
              key={index.toString()}
              cursor="pointer"
              color={!isActive ? "green.200" : "green.500"}
              opacity={isActive ? 1 : 0.5}
              p={2}
              borderRadius="md"
              onClick={() => {
                setActiveTransactionSource(sourceGroup);
              }}
            >
              <Tag.Label>{sourceGroup.transaction_source_name}</Tag.Label>
            </Tag.Root>
          );
        })}
      </HStack>
    </Box>
  );
}
