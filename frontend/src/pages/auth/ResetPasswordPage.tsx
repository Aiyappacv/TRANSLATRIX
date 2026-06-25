import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { KeyRound } from "lucide-react";
import { authApi } from "@/services/authApi";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert } from "@/components/ui/alert";

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const [token, setToken] = useState(searchParams.get("token") ?? "");
  const [password, setPassword] = useState("");
  const mutation = useMutation({ mutationFn: authApi.resetPassword });
  const canSubmit = token.trim().length > 0 && password.length >= 8;

  return (
    <Card className="shadow-enterprise">
      <CardHeader><CardTitle>Reset password</CardTitle><CardDescription>Create a new password for your TRANSLATRIX PRO account.</CardDescription></CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2"><Label htmlFor="reset-token">Reset token</Label><Input id="reset-token" value={token} onChange={(event) => setToken(event.target.value)} autoComplete="one-time-code" /></div>
        <div className="space-y-2"><Label htmlFor="new-password">New password</Label><Input id="new-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="new-password" /></div>
        <Button className="w-full" disabled={!canSubmit || mutation.isPending} onClick={() => mutation.mutate({ token: token.trim(), password })}><KeyRound className="h-4 w-4" />Reset password</Button>
        {mutation.isSuccess ? <Alert tone="success">Password reset complete. You can now sign in.</Alert> : null}
        {mutation.isError ? <Alert tone="danger">{mutation.error instanceof Error ? mutation.error.message : "Password reset failed."}</Alert> : null}
        <Link className="block text-center text-sm text-primary" to="/auth/login">Back to login</Link>
      </CardContent>
    </Card>
  );
}
