import type * as React from "react";
import { Menu } from "lucide-react";
import { AppSidebar } from "./AppSidebar";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";

export function MobileSidebarDrawer() {
  return (
    <Dialog>
      <DialogTrigger asChild><Button variant="outline" size="icon" className="lg:hidden" aria-label="Open main navigation"><Menu className="h-4 w-4" /></Button></DialogTrigger>
      <DialogContent className="left-0 top-0 h-screen max-w-[320px] translate-x-0 translate-y-0 p-0">
        <div className="[&_aside]:static [&_aside]:flex [&_aside]:w-full"><AppSidebar /></div>
      </DialogContent>
    </Dialog>
  );
}
