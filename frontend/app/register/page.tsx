"use client";
import { ChangeEvent, FormEvent, ReactNode, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import GoogleButton from "@/component/GoogleButton";

const API = process.env.NEXT_PUBLIC_API_URL;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type Field = "name" | "email" | "password" | "confirm";
type Values = Record<Field, string>;
type Errors = Partial<Record<Field, string>>;

function validate(v: Values): Errors {
  const e: Errors = {};

  const name = v.name.trim();
  if (!name) e.name = "Full name is required";
  else if (name.length < 2) e.name = "Name must be at least 2 characters";
  else if (name.length > 50) e.name = "Name must be 50 characters or fewer";

  const email = v.email.trim();
  if (!email) e.email = "Email is required";
  else if (!EMAIL_RE.test(email)) e.email = "Enter a valid email address";

  if (!v.password) e.password = "Password is required";
  else if (v.password.length < 8) e.password = "Password must be at least 8 characters";
  else if (!/[A-Za-z]/.test(v.password) || !/\d/.test(v.password))
    e.password = "Password must contain at least one letter and one number";

  if (!v.confirm) e.confirm = "Please confirm your password";
  else if (v.confirm !== v.password) e.confirm = "Passwords do not match";

  return e;
}

function FieldWrap({ label, error, children }: { label: string; error?: string; children: ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-slate-700">{label}</label>
      {children}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}

export default function RegisterPage() {
  const router = useRouter();
  const [values, setValues] = useState<Values>({ name: "", email: "", password: "", confirm: "" });
  const [touched, setTouched] = useState<Partial<Record<Field, boolean>>>({});
  const [submitted, setSubmitted] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState("");
  const [loading, setLoading] = useState(false);

  const errors = validate(values);
  // Show a field's error only after the user left it or pressed the button
  const errorFor = (f: Field) => (touched[f] || submitted ? errors[f] : undefined);

  const inputClass = (f: Field) =>
    `w-full rounded-lg border bg-white px-3 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 ${
      errorFor(f)
        ? "border-red-400 focus:border-red-500 focus:ring-red-100"
        : "border-slate-300 focus:border-blue-500 focus:ring-blue-200"
    }`;

  const onChange = (f: Field) => (e: ChangeEvent<HTMLInputElement>) => {
    setValues((v) => ({ ...v, [f]: e.target.value }));
    setServerError("");
  };
  const onBlur = (f: Field) => () => setTouched((t) => ({ ...t, [f]: true }));

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitted(true);
    setServerError("");
    if (Object.keys(errors).length > 0) return; // stop here if anything is invalid

    setLoading(true);
    try {
      const res = await fetch(`${API}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: values.name.trim(),
          email: values.email.trim(),
          password: values.password,
        }),
      });

      const text = await res.text();
      let data: { error?: string } = {};
      try {
        data = JSON.parse(text);
      } catch {
        throw new Error(`Server returned an unexpected response (status ${res.status}).`);
      }
      if (!res.ok) throw new Error(data.error || "Registration failed");

      router.push("/login?registered=1");
    } catch (err) {
      const message = (err as Error).message;
      setServerError(
        message === "Failed to fetch" ? "Cannot reach the server. Please try again in a moment." : message
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-10">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600 text-xl font-bold text-white">
            T
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Create your account</h1>
          <p className="mt-1 text-sm text-slate-500">Start assigning and tracking tasks with TaskFlow.</p>
        </div>

        {serverError && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {serverError}
          </div>
        )}

        {/* noValidate turns off the browser's own popups so our messages show instead */}
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <FieldWrap label="Full name" error={errorFor("name")}>
            <input
              className={inputClass("name")}
              value={values.name}
              onChange={onChange("name")}
              onBlur={onBlur("name")}
              placeholder="Your name"
              maxLength={60}
              aria-invalid={!!errorFor("name")}
            />
          </FieldWrap>

          <FieldWrap label="Email" error={errorFor("email")}>
            <input
              type="email"
              className={inputClass("email")}
              value={values.email}
              onChange={onChange("email")}
              onBlur={onBlur("email")}
              placeholder="you@example.com"
              aria-invalid={!!errorFor("email")}
            />
          </FieldWrap>

          <FieldWrap label="Password" error={errorFor("password")}>
            <input
              type={showPassword ? "text" : "password"}
              className={inputClass("password")}
              value={values.password}
              onChange={onChange("password")}
              onBlur={onBlur("password")}
              placeholder="At least 8 characters, with a letter and a number"
              aria-invalid={!!errorFor("password")}
            />
          </FieldWrap>

          <FieldWrap label="Confirm password" error={errorFor("confirm")}>
            <input
              type={showPassword ? "text" : "password"}
              className={inputClass("confirm")}
              value={values.confirm}
              onChange={onChange("confirm")}
              onBlur={onBlur("confirm")}
              placeholder="Repeat your password"
              aria-invalid={!!errorFor("confirm")}
            />
          </FieldWrap>

          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={showPassword} onChange={(e) => setShowPassword(e.target.checked)} />
            Show passwords
          </label>

          <button
            disabled={loading}
            className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>

        <div className="my-5 flex items-center gap-3 text-xs text-slate-400">
          <div className="h-px flex-1 bg-slate-200" /> OR <div className="h-px flex-1 bg-slate-200" />
        </div>

        <GoogleButton label="Sign up with Google" />

        <p className="mt-6 text-center text-sm text-slate-600">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-blue-600 hover:underline">
            Log in
          </Link>
        </p>
      </div>
    </main>
  );
}