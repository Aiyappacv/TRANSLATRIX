import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Eye, EyeOff, KeyRound, Loader2, LockKeyhole, ShieldCheck } from "lucide-react";
import { loginSchema, type LoginInput } from "@/schemas/auth.schema";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { APP_NAME } from "@/utils/constants";
import { isAuthSession, type AuthSession, type MfaChallenge } from "@/types";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();
  const { login, loginStatus, verifyMfa, verifyMfaStatus } = useAuth();
  const [challenge, setChallenge] = useState<MfaChallenge | null>(null);
  const [code, setCode] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const from = (location.state as { from?: string } | null)?.from ?? "/app/dashboard";
  const form = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const finishLogin = (session: AuthSession) => {
    toast.success("Secure session started", "Company, role, and RBAC profile loaded");
    const destination = from === "/app/dashboard" && session.user.roles.includes("spectra_super_admin") ? "/super-admin/dashboard" : from;
    navigate(destination, { replace: true });
  };

  const onSubmit = async (input: LoginInput) => {
    try {
      const result = await login(input);
      if (isAuthSession(result)) {
        finishLogin(result);
        return;
      }
      setChallenge(result);
      setCode("");
      toast.info(result.mfaSetupRequired ? "Set up MFA" : "MFA verification required", "Enter the six-digit code from your authenticator app.");
    } catch (error) {
      toast.error("Unable to sign in", error instanceof Error ? error.message : "Check your credentials");
    }
  };

  const submitMfa = async () => {
    if (!challenge || !/^\d{6}$/.test(code)) {
      toast.error("Enter a valid code", "The authenticator code must contain six digits.");
      return;
    }
    try {
      const session = await verifyMfa({ challengeToken: challenge.challengeToken, code });
      finishLogin(session);
    } catch (error) {
      toast.error("MFA verification failed", error instanceof Error ? error.message : "Check the code and try again");
    }
  };

  return (
    <div className="auth-wide mx-auto max-w-md">
      <Card className="shadow-enterprise">
        <CardHeader>
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-gradient text-white dark:bg-indigo-600">{challenge ? <KeyRound className="h-5 w-5" /> : <LockKeyhole className="h-5 w-5" />}</div>
          <CardTitle className="text-2xl">{challenge ? "Verify multi-factor authentication" : `Sign in to ${APP_NAME}`}</CardTitle>
          <CardDescription className="dark:text-slate-400">{challenge ? `A six-digit verification code is required for ${challenge.email}.` : "Enter the credentials issued by your organization."}</CardDescription>
        </CardHeader>
        <CardContent>
          {challenge ? (
            <div className="space-y-4">
              {challenge.mfaSetupRequired && challenge.secret ? (
                <div className="rounded-xl border bg-slate-50 p-4 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                  <p className="font-semibold">Authenticator setup</p>
                  <p className="mt-1">Add this account to an authenticator app, then enter the generated code.</p>
                  <code className="mt-3 block break-all rounded-lg bg-white p-3 font-mono text-xs dark:bg-slate-950 dark:text-slate-200">{challenge.secret}</code>
                </div>
              ) : null}
              <div className="space-y-2">
                <Label htmlFor="mfa-code">Six-digit code</Label>
                <Input id="mfa-code" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))} autoFocus />
              </div>
              <Button type="button" className="w-full" disabled={verifyMfaStatus === "pending"} onClick={submitMfa}>
                {verifyMfaStatus === "pending" ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
                Verify and sign in
              </Button>
              <Button type="button" variant="outline" className="w-full" onClick={() => { setChallenge(null); setCode(""); }}>Back to sign in</Button>
            </div>
          ) : (
            <>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Work email</Label>
                  <Input id="email" type="email" autoComplete="email" autoFocus {...form.register("email")} />
                  {form.formState.errors.email ? <p className="text-xs text-danger">{form.formState.errors.email.message}</p> : null}
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between"><Label htmlFor="password">Password</Label><Link className="text-xs font-semibold text-primary hover:underline" to="/auth/forgot-password">Forgot password?</Link></div>
                  <div className="relative">
                    <Input id="password" type={showPassword ? "text" : "password"} autoComplete="current-password" className="pr-10" {...form.register("password")} />
                    <button type="button" onClick={() => setShowPassword((prev) => !prev)} className="absolute right-2 top-1/2 -translate-y-1/2 flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 focus-ring" aria-label={showPassword ? "Hide password" : "Show password"}>
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  {form.formState.errors.password ? <p className="text-xs text-danger">{form.formState.errors.password.message}</p> : null}
                </div>
                <Button type="submit" className="w-full" disabled={loginStatus === "pending"}>
                  {loginStatus === "pending" ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
                  Sign in securely
                </Button>
              </form>
              <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">New company? <Link className="font-semibold text-primary hover:underline" to="/auth/register">Register tenant</Link></p>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
