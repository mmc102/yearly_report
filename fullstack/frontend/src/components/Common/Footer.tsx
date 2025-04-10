import { Box, Flex, Link, Text } from "@chakra-ui/react";

export function Footer() {
  return (
    <Box as="footer" w="100%" py={6}>
      <Flex
        maxW="1200px"
        alignSelf={'flex-end'}
        mx="auto"
        p={6}
        justify="space-between"
        align="center"
        flexWrap="wrap"
      >
        <Text fontSize="lg" fontWeight="bold">

        </Text>

        <Flex gap={6} flexWrap="wrap">
          <Link href="/contact-me" _hover={{ textDecoration: "underline" }}>
            Contact Me
          </Link>
          <Link href="/how" _hover={{ textDecoration: "underline" }}>
            How Do I Use This?
          </Link>
          <Link href="/faq" _hover={{ textDecoration: "underline" }}>
            FAQ
          </Link>
          <Link href="/privacy" _hover={{ textDecoration: "underline" }}>
            Privacy Policy
          </Link>
          <Link href="/terms" _hover={{ textDecoration: "underline" }}>
            Terms of Service
          </Link>
        </Flex>
      </Flex>
    </Box>
  );
}
