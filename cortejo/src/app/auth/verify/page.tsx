"use client";

import { Suspense, useState, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "motion/react";
import { AlertCircle } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { verifyMagicLink } from "@/lib/actions";

function VerifyContent() {
  const searchParams = useSearchParams();
  const tokenParam = searchParams.get("token");
  const router = useRouter();
  const { login } = useAuth();
  const [error, setError] = useState(false);
  const [verifying, setVerifying] = useState(true);
  const started = useRef(false);

  if (!started.current) {
    started.current = true;
    if (!tokenParam) {
      setError(true);
      setVerifying(false);
    } else {
      verifyMagicLink(tokenParam).then((result) => {
        if ("error" in result) {
          setError(true);
        } else {
          login(result.user);
          router.push("/chat");
          return;
        }
        setVerifying(false);
      }).catch(() => {
        setError(true);
        setVerifying(false);
      });
    }
  }

  if (verifying) {
    return (
      <div className="min-h-[100dvh] flex flex-col items-center justify-center bg-white dark:bg-[#212121] p-4">
        <div className="flex items-center gap-3 text-zinc-500 dark:text-zinc-400">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
            className="w-5 h-5 border-2 border-current border-t-transparent rounded-full"
          />
          Verificando seu acesso...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-[100dvh] flex flex-col items-center justify-center bg-white dark:bg-[#212121] p-4">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center max-w-sm"
        >
          <AlertCircle className="w-12 h-12 text-zinc-400 dark:text-zinc-500 mx-auto mb-4" />
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100 mb-2">
            Link expirado ou inválido
          </h1>
          <p className="text-zinc-500 dark:text-zinc-400 mb-6">
            Este link de acesso já foi usado ou expirou. Solicite um novo link para entrar.
          </p>
          <Link
            href="/login"
            className="inline-flex items-center justify-center bg-black dark:bg-white text-white dark:text-black py-3.5 px-8 rounded-full font-medium hover:opacity-80 transition-opacity"
          >
            Solicitar novo link
          </Link>
        </motion.div>
      </div>
    );
  }

  return null;
}

export default function VerifyPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-[100dvh] flex items-center justify-center bg-white dark:bg-[#212121]">
          <div className="flex items-center gap-3 text-zinc-500 dark:text-zinc-400">
            <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
            Verificando seu acesso...
          </div>
        </div>
      }
    >
      <VerifyContent />
    </Suspense>
  );
}
