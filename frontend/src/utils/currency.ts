export const currencies = ["USD", "EUR", "INR", "GBP", "AED", "SGD", "JPY"] as const;
export type CurrencyCode = (typeof currencies)[number];
