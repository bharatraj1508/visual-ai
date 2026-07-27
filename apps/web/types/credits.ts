export interface CreditBalance {
  available: number;
  held: number;
  total: number;
}

export interface CreditPack {
  id: string;
  slug: string;
  name: string;
  base_credits: number;
  bonus_credits: number;
  total_credits: number;
  badge: string | null;
  sort_order: number;
}

export interface EstimateResponse {
  cost: number;
  balance: number;
  affordable: boolean;
}

export interface Purchase {
  id: string;
  credits_granted: number;
  price_minor: number;
  currency: string;
  status: string;
  created_at: string;
}

export interface LedgerEntry {
  id: string;
  entry_type: string;
  amount: number;
  bucket: string;
  balance_after: number;
  reason: string | null;
  related_report_id: string | null;
  related_purchase_id: string | null;
  expires_at: string | null;
  created_at: string;
}
