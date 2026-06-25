import { Link } from "react-router-dom";
import { FileUp, Link2, PlusCircle, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Can } from "@/components/common/Can";
import { permissions } from "@/utils/permissions";

export function QuickActionsPanel() {
  return (
    <div className="hidden items-center gap-1.5 xl:flex">
      <Can permissions={[permissions.ingestionManage]}><Button asChild size="sm" variant="outline" className="h-8 gap-1.5 px-2.5 text-xs"><Link to="/app/ingestion/shared-links/new"><Link2 className="h-3.5 w-3.5" />Shared link</Link></Button></Can>
      <Can permissions={[permissions.filesUpload]}><Button asChild size="sm" variant="outline" className="h-8 gap-1.5 px-2.5 text-xs"><Link to="/app/files"><FileUp className="h-3.5 w-3.5" />Files</Link></Button></Can>
      <Can permissions={[permissions.entriesManage]}><Button asChild size="sm" variant="outline" className="h-8 gap-1.5 px-2.5 text-xs"><Link to="/app/entries"><PlusCircle className="h-3.5 w-3.5" />Entries</Link></Button></Can>
      <Can permissions={[permissions.postingExecute]}><Button asChild size="sm" className="h-8 gap-1.5 px-2.5 text-xs"><Link to="/app/posting/sap"><Send className="h-3.5 w-3.5" />Post</Link></Button></Can>
    </div>
  );
}
