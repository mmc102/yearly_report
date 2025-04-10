"use client";

import {
  Button,
  Container,
  Field,
  Flex,
  Input,
  Link,
  Box,
  Text,
} from "@chakra-ui/react";
import useCustomToast from "../../hooks/useCustomToast";
import { OauthService } from "@/client";
import { FcGoogle } from "react-icons/fc";
import {
  Link as RouterLink,
  createFileRoute,
} from "@tanstack/react-router";
import { type SubmitHandler, useForm } from "react-hook-form";
import { useState, useEffect } from "react";
import { useNavigate } from "@tanstack/react-router";

import type { UserRegister } from "@/client";
import useAuth  from "@/hooks/useAuth";
import { confirmPasswordRules, emailPattern, passwordRules } from "../../utils";

export const Route = createFileRoute("/_layout/signup")({
  component: SignUp,

});

interface UserRegisterForm extends UserRegister {
  confirm_password: string;
}

function SignUp() {
  const showToast = useCustomToast();
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const handleGoogleLogin = async () => {
    try {
      setIsGoogleLoading(true);
      const { url } = await OauthService.loginGoogle();

      if (url) {
        // Redirect to Google's authorization page
        window.location.href = url;
      } else {
        showToast("Error", "Failed to initiate Google login", "error");
      }
    } catch (error) {
      console.error("Google login error:", error);
      showToast(
        "Error",
        "Failed to connect to authentication service",
        "error"
      );
    } finally {
      setIsGoogleLoading(false);
    }
  };

  const { signUpMutation, requires2FA, requires2FASetup } = useAuth();
  const navigate = useNavigate();
  
  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<UserRegisterForm>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      email: "",
      full_name: "",
      password: "",
      confirm_password: "",
    },
  });

  const onSubmit: SubmitHandler<UserRegisterForm> = async (data) => {
    if (isSubmitting) return;

    try {
      await signUpMutation.mutateAsync(data);
    } catch (error) {
      console.error(error);
    }
  };
  
  return (
    <Flex flexDir={{ base: "column", md: "row" }} justify="center" h="100vh">
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
        <Button
          variant="outline"
          onClick={handleGoogleLogin}
          disabled={isGoogleLoading}
        >
          <Flex align="center">
            <Box mr={2}>
              <FcGoogle size={20} />
            </Box>
            <Text>Sign in with Google</Text>
          </Flex>
        </Button>

        <Flex align="center" my={4}>
          <Box flex="1" h="1px" bg="gray.200" />
          <Text px={3} fontSize="sm" color="gray.500">
            OR
          </Text>
          <Box flex="1" h="1px" bg="gray.200" />
        </Flex>


        <Field.Root invalid={!!errors.full_name}>
          <Field.Label>Full Name</Field.Label>
          <Input
            id="full_name"
            minLength={3}
            {...register("full_name", { required: "Full Name is required" })}
            placeholder="Full Name"
            autoComplete="name"
            type="text"
          />
          {errors.full_name && (
            <Field.ErrorText>{errors.full_name.message}</Field.ErrorText>
          )}
        </Field.Root>

        <Field.Root invalid={!!errors.email}>
          <Field.Label>Email</Field.Label>
          <Input
            id="email"
            {...register("email", {
              required: "Email is required",
              pattern: emailPattern,
            })}
            placeholder="Email"
            autoComplete="username"
            type="email"
          />
          {errors.email && (
            <Field.ErrorText>{errors.email.message}</Field.ErrorText>
          )}
        </Field.Root>

        <Field.Root invalid={!!errors.password}>
          <Field.Label>Password</Field.Label>
          <Input
            id="password"
            {...register("password", passwordRules())}
            placeholder="Password"
            autoComplete="new-password"
            type="password"
          />
          {errors.password && (
            <Field.ErrorText>{errors.password.message}</Field.ErrorText>
          )}
        </Field.Root>

        <Field.Root invalid={!!errors.confirm_password}>
          <Field.Label>Confirm Password</Field.Label>
          <Input
            id="confirm_password"
            {...register("confirm_password", confirmPasswordRules(getValues))}
            placeholder="Repeat Password"
            autoComplete="new-password"
            type="password"
          />
          {errors.confirm_password && (
            <Field.ErrorText>{errors.confirm_password.message}</Field.ErrorText>
          )}
        </Field.Root>

        <Button variant="outline" type="submit" loading={isSubmitting}>
          Sign Up
        </Button>



        <Text>
          Already have an account?{" "}
          <RouterLink to="/login" color="blue.500">
            <Link color="blue.500">Log In</Link>
          </RouterLink>
        </Text>
      </Container>
    </Flex>
  );
}

export default SignUp;
