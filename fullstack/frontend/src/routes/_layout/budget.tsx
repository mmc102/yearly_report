import { BudgetsService } from "@/client";
import { isLoggedIn } from "@/hooks/useAuth";
import {
  Container,
  Box,
  Text,
  Button,
  Flex,
  Heading,
  Input,
  HStack,
} from "@chakra-ui/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { ManageBudget } from "@/components/Common/BudgetManager";

export const Route = createFileRoute("/_layout/budget")({
  component: ManageBudgets,
});

function ManageBudgets() {
  const {
    data: budget,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["budgets"],
    queryFn: BudgetsService.getBudget,
    enabled: isLoggedIn(),
  });

  if (isError) {
    return (
      <Container maxW="full">
        <Heading size="lg" textAlign="center" py={12}>
          Failed to Load Budgets
        </Heading>
      </Container>
    );
  }

  if (isLoading) {
    return (
      <Container maxW="full">
        <Heading size="lg" textAlign="center" py={12}>
          Loading...
        </Heading>
      </Container>
    );
  }

  return (
    <Container mt={24} maxW="large">
      {budget ? (
        <ManageBudget budget={budget} />
      ) : (
        <Flex justifyContent="center">
          <CreateNewBudget />
        </Flex>
      )}
    </Container>
  );
}

function CreateNewBudget() {
  const queryClient = useQueryClient();
  const [budgetName, setBudgetName] = useState<string>("My Budget");

  const addBudgetMutation = useMutation({
    mutationFn: () =>
      BudgetsService.createBudget({
        requestBody: { name: budgetName },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["budgets"] });
      setBudgetName("");
    },
  });

  return (
    <Box>
      <Text>You don't have a budget yet.</Text>
      <HStack mt={4}>
        <Input
          maxWidth="md"
          value={budgetName}
          onChange={(e) => setBudgetName(e.target.value)}
        ></Input>
        <Button size="sm" onClick={() => addBudgetMutation.mutate()}>
          Create Budget
        </Button>
      </HStack>
    </Box>
  );
}
