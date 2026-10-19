import { Suspense } from "react";
import { LoginForm } from "@/components/shell/LoginForm";

export const metadata = { title: "Sign in · Emami — Distributor Experience Platform" };

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
