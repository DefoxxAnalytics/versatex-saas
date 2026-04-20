import { useState } from "react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Lock, User, AlertCircle } from "lucide-react";
import { authAPI } from "@/lib/api";
import { setUserData } from "@/lib/auth";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";
import { useTheme } from "@/contexts/ThemeContext";
import { cn } from "@/lib/utils";

export default function Login() {
  const [, setLocation] = useLocation();
  const { checkAuth } = useAuth();
  const { colorScheme } = useTheme();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  // Color scheme-aware styles
  const isNavy = colorScheme === "navy";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!username || !password) {
      setError("Please enter both username and password");
      return;
    }

    setIsLoading(true);

    try {
      // Login request - tokens are set as HTTP-only cookies by the server
      const response = await authAPI.login({
        username,
        password,
      });

      // Store user info (tokens are in HTTP-only cookies, not accessible to JS)
      if (response.data.user) {
        setUserData(response.data.user);
      }

      toast.success("Login successful");

      // Update auth context and redirect after a brief delay to ensure state updates
      checkAuth();

      // Use setTimeout to ensure state update completes before navigation
      setTimeout(() => {
        setLocation("/");
      }, 100);
    } catch (error: any) {
      // Only log in development to prevent information leakage
      if (import.meta.env.DEV) {
        console.error("Login error:", error);
      }

      // Sanitize error messages - map all errors to user-friendly messages
      // to prevent backend system information leakage
      if (error.response?.status === 401) {
        setError("Invalid username or password");
      } else if (error.response?.status === 429) {
        setError("Too many login attempts. Please try again later.");
      } else if (error.response?.status >= 500) {
        setError("Server error. Please try again later.");
      } else {
        // Generic message for all other errors - don't expose backend details
        setError("Login failed. Please check your credentials and try again.");
      }

      toast.error("Login failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className={cn(
        "min-h-screen flex items-center justify-center p-4 transition-colors duration-300",
        isNavy
          ? "bg-[#1e3a8a]"
          : "bg-gradient-to-br from-indigo-50 via-white to-cyan-50",
      )}
    >
      <div className="w-full max-w-md">
        {/* Login Card */}
        <Card className="border-0 shadow-2xl">
          <CardHeader className="space-y-4 pb-8">
            <div className="flex justify-center">
              <img
                src="/vtx_logo2.png"
                alt="Versatex Logo"
                className="h-24 w-auto"
              />
            </div>
            <div className="text-center">
              <CardTitle className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">
                Analytics Dashboard
              </CardTitle>
              <CardDescription className="text-base mt-2">
                Sign in to access your procurement analytics
              </CardDescription>
            </div>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Error Message */}
              {error && (
                <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0" />
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              )}

              {/* Username Field */}
              <div className="space-y-2">
                <label
                  htmlFor="username"
                  className="text-sm font-medium text-gray-700"
                >
                  Username
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <Input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Enter your username"
                    className="h-12 text-base pl-10"
                    disabled={isLoading}
                    autoFocus
                  />
                </div>
              </div>

              {/* Password Field */}
              <div className="space-y-2">
                <label
                  htmlFor="password"
                  className="text-sm font-medium text-gray-700"
                >
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="h-12 text-base pl-10"
                    disabled={isLoading}
                  />
                </div>
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                className={cn(
                  "w-full h-12 text-base transition-all duration-300",
                  isNavy
                    ? "bg-[#1e3a8a] hover:bg-[#1e40af] shadow-[0_4px_12px_rgba(30,58,138,0.4)]"
                    : "bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 shadow-lg",
                )}
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2" />
                    Signing in...
                  </>
                ) : (
                  <>
                    <Lock className="h-5 w-5 mr-2" />
                    Sign In
                  </>
                )}
              </Button>
            </form>

            {/* Help Text */}
            <div className="mt-6 text-center">
              <p className="text-sm text-gray-600">
                Use the superuser credentials you created
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <p
          className={cn(
            "text-center text-sm mt-6 transition-colors duration-300",
            isNavy ? "text-white/70" : "text-gray-600",
          )}
        >
          Protected by JWT authentication
        </p>
      </div>
    </div>
  );
}
