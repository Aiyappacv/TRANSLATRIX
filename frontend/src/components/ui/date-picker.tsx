import * as React from "react";
import { Input } from "@/components/ui/input";

export const DatePicker = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>((props, ref) => (
  <Input ref={ref} type="date" {...props} />
));
DatePicker.displayName = "DatePicker";
