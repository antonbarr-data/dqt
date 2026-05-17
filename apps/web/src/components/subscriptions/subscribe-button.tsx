"use client";

import { useState } from "react";
import { Bell, BellOff } from "lucide-react";

interface SubscribeButtonProps {
  metricFqn: string;
  userId?: string;
}

export function SubscribeButton({ metricFqn, userId = "demo" }: SubscribeButtonProps) {
  const [subscribed, setSubscribed] = useState(false);
  const [loading, setLoading] = useState(false);

  async function toggle() {
    if (subscribed) return; // subscribe-only in M4; unsubscribe via /subscriptions page
    setLoading(true);
    try {
      await fetch("/api/v1/subscriptions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          metric_fqns: [metricFqn],
          cadence: "on_threshold",
          delivery_channels: ["email"],
        }),
      });
      setSubscribed(true);
    } catch (_) {
      // ignore -- state unchanged
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      onClick={toggle}
      disabled={loading}
      className="flex items-center gap-1.5 t-small hover:opacity-70 transition-opacity disabled:opacity-40"
      style={{ color: subscribed ? "var(--accent)" : "var(--fg-2)" }}
      title={
        subscribed
          ? "Subscribed -- manage via /subscriptions"
          : "Subscribe to threshold alerts for this metric"
      }
    >
      {subscribed ? (
        <BellOff size={14} strokeWidth={1.6} />
      ) : (
        <Bell size={14} strokeWidth={1.6} />
      )}
      {subscribed ? "Subscribed" : "Subscribe"}
    </button>
  );
}
