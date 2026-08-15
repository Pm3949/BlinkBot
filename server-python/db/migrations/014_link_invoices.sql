-- Link credit transactions to invoices
ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS invoice_id UUID REFERENCES invoices(id) ON DELETE SET NULL;
