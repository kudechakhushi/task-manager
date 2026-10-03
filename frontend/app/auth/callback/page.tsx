"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AuthCallback() {
  const router = useRouter();

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("token");
    if (token) {
      localStorage.setItem("token", token);
      router.replace("/dashboard");
    } else {
      router.replace("/");
    }
  }, [router]);

  return <p className="p-6">Signing you in...</p>;
}