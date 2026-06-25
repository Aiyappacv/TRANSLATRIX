import Editor from "@monaco-editor/react";

interface MonacoJsonViewerProps {
  value: string;
  height: number;
}

export default function MonacoJsonViewer({ value, height }: MonacoJsonViewerProps) {
  return (
    <Editor
      height={height}
      defaultLanguage="json"
      value={value}
      theme="vs-dark"
      options={{
        readOnly: true,
        minimap: { enabled: false },
        fontSize: 13,
        scrollBeyondLastLine: false,
        wordWrap: "on",
        automaticLayout: true,
      }}
    />
  );
}
