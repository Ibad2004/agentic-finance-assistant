const GBP_FORMATTER = new Intl.NumberFormat("en-GB", {
  style: "currency",
  currency: "GBP",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatCurrency(amount: number): string {
  return GBP_FORMATTER.format(amount);
}

const DATE_FORMATTER = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

export function formatDate(date: string): string {
  const d = new Date(date);
  return DATE_FORMATTER.format(d);
}

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

export function formatDateTime(date: string): string {
  const d = new Date(date);
  return DATE_TIME_FORMATTER.format(d);
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function getStatusColor(status: string): string {
  switch (status) {
    case "under_budget":
      return "text-emerald-400";
    case "near_limit":
      return "text-amber-400";
    case "over_budget":
      return "text-red-400";
    default:
      return "text-slate-400";
  }
}

export function getStatusBg(status: string): string {
  switch (status) {
    case "under_budget":
      return "bg-emerald-400/10 border-emerald-400/20";
    case "near_limit":
      return "bg-amber-400/10 border-amber-400/20";
    case "over_budget":
      return "bg-red-400/10 border-red-400/20";
    default:
      return "bg-slate-400/10 border-slate-400/20";
  }
}

export function getStatusLabel(status: string): string {
  switch (status) {
    case "under_budget":
      return "Under Budget";
    case "near_limit":
      return "Near Limit";
    case "over_budget":
      return "Over Budget";
    default:
      return status;
  }
}

export function getCategoryIcon(category: string): string {
  const iconMap: Record<string, string> = {
    "salary": "Briefcase",
    "freelance income": "Laptop",
    "other income": "TrendingUp",
    "housing": "Home",
    "food": "UtensilsCrossed",
    "transport": "Car",
    "utilities": "Zap",
    "healthcare": "Heart",
    "shopping": "ShoppingBag",
    "entertainment": "Film",
    "subscriptions": "RefreshCw",
    "education": "GraduationCap",
    "insurance": "Shield",
    "personal care": "Sparkles",
    "other expense": "MoreHorizontal",
  };
  return iconMap[category.toLowerCase()] ?? "Circle";
}

export function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}
