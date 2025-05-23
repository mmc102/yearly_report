"use client";

import {
  Button,
  Container,
  Field,
  Heading,
  Input,
  Text,
} from "@chakra-ui/react";
import { useMutation } from "@tanstack/react-query";
import { createFileRoute, redirect } from "@tanstack/react-router";
import { type SubmitHandler, useForm } from "react-hook-form";

import { type ApiError, LoginService } from "@/client";
import { isSessionActive } from "@/hooks/useAuth";
import useCustomToast from "@/hooks/useCustomToast";
import { emailPattern, handleError } from "../../utils";

interface FormData {
  email: string;
}

export const Route = createFileRoute("/_layout/recover-password")({
  component: RecoverPassword,
  beforeLoad: async () => {
    if (await isSessionActive()) {
      throw redirect({
        to: "/",
      });
    }
  },
});

function RecoverPassword() {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>();
  const showToast = useCustomToast();

  const recoverPassword = async (data: FormData) => {
    await LoginService.recoverPassword({
      email: data.email,
    });
  };

  const mutation = useMutation({
    mutationFn: recoverPassword,
    onSuccess: () => {
      showToast(
        "Email sent.",
        "We sent an email with a link to get back into your account.",
        "success",
      );
      reset();
    },
    onError: (err: ApiError) => {
      handleError(err, showToast);
    },
  });

  const onSubmit: SubmitHandler<FormData> = async (data) => {
    mutation.mutate(data);
  };

  return (
    <Container
      as="form"
      onSubmit={handleSubmit(onSubmit)}
      h="100vh"
      maxW="sm"
      alignItems="stretch"
      justifyContent="center"
      gap={4}
      centerContent
    >
      <Heading size="xl" color="ui.main" textAlign="center" mb={2}>
        Password Recovery
      </Heading>
      <Text>
        A password recovery email will be sent to the registered account.
      </Text>

      <Field.Root>
        <Field.Label>Email</Field.Label>
        <Input
          id="email"
          {...register("email", {
            required: "Email is required",
            pattern: emailPattern,
          })}
          placeholder="Email"
          type="email"
        />
        {errors.email && (
          <Field.ErrorText>{errors.email.message}</Field.ErrorText>
        )}
      </Field.Root>

      <Button variant="outline" type="submit" loading={isSubmitting}>
        Continue
      </Button>
    </Container>
  );
}

export default RecoverPassword;
