import type * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/utils/cn";

export const Drawer = DialogPrimitive.Root;
export const DrawerTrigger = DialogPrimitive.Trigger;
export const DrawerClose = DialogPrimitive.Close;
export const DrawerPortal = DialogPrimitive.Portal;

export const DrawerOverlay = ({ className, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>) => (
  <DialogPrimitive.Overlay className={cn("fixed inset-0 z-50 bg-slate-950/50 backdrop-blur-sm", className)} {...props} />
);

interface DrawerContentProps extends React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> {
  side?: "left" | "right" | "top" | "bottom";
}

const sideClasses = {
  left: "inset-y-0 left-0 h-full w-[min(92vw,28rem)] border-r",
  right: "inset-y-0 right-0 h-full w-[min(92vw,28rem)] border-l",
  top: "inset-x-0 top-0 max-h-[85vh] w-full border-b",
  bottom: "inset-x-0 bottom-0 max-h-[85vh] w-full border-t",
};

export const DrawerContent = ({ className, children, side = "right", ...props }: DrawerContentProps) => (
  <DrawerPortal>
    <DrawerOverlay />
    <DialogPrimitive.Content
      className={cn(
        "fixed z-50 overflow-y-auto border-slate-200 bg-white p-6 shadow-2xl outline-none dark:border-slate-800 dark:bg-slate-950",
        sideClasses[side],
        className,
      )}
      {...props}
    >
      {children}
      <DialogPrimitive.Close aria-label="Close drawer" className="absolute right-4 top-4 rounded-lg p-1 opacity-70 focus-ring hover:bg-slate-100 hover:opacity-100 dark:hover:bg-slate-900">
        <X className="h-4 w-4" />
      </DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </DrawerPortal>
);

export const DrawerHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => <div className={cn("mb-5 flex flex-col space-y-1.5 text-left", className)} {...props} />;
export const DrawerTitle = ({ className, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>) => <DialogPrimitive.Title className={cn("text-lg font-semibold", className)} {...props} />;
export const DrawerDescription = ({ className, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>) => <DialogPrimitive.Description className={cn("text-sm text-slate-500", className)} {...props} />;
export const DrawerFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => <div className={cn("mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end", className)} {...props} />;
