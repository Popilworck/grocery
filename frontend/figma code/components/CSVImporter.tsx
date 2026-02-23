import { useState, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Alert, AlertDescription } from "./ui/alert";
import { 
  Upload, 
  FileSpreadsheet, 
  CheckCircle2, 
  AlertTriangle,
  X,
  Database
} from "lucide-react";
import { InventoryData } from "../App";

interface CSVImporterProps {
  onImport: (data: InventoryData[]) => void;
}

export function CSVImporter({ onImport }: CSVImporterProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [parsedData, setParsedData] = useState<InventoryData[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const parseCSV = (text: string): InventoryData[] => {
    const lines = text.split('\n').filter(line => line.trim());
    if (lines.length < 2) {
      throw new Error("CSV file must contain headers and at least one data row");
    }

    const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
    const data: InventoryData[] = [];

    // Expected headers: produce_id, name, quantity, supplier, price, category
    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(',').map(v => v.trim());
      if (values.length !== headers.length) continue;

      const row: any = {};
      headers.forEach((header, index) => {
        row[header] = values[index];
      });

      data.push({
        produce_id: row.produce_id || row.id || '',
        name: row.name || row.product_name || '',
        quantity: parseInt(row.quantity || '0'),
        supplier: row.supplier || undefined,
        price: parseFloat(row.price || '0') || undefined,
        category: row.category || undefined
      });
    }

    return data;
  };

  const handleFile = async (file: File) => {
    setError(null);
    setSuccess(false);
    
    if (!file.name.endsWith('.csv')) {
      setError("Please upload a CSV file");
      return;
    }

    setUploadedFile(file);

    try {
      const text = await file.text();
      const data = parseCSV(text);
      setParsedData(data);
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to parse CSV file");
      setParsedData([]);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFile(file);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFile(file);
    }
  };

  const handleImport = () => {
    if (parsedData.length > 0) {
      onImport(parsedData);
      setSuccess(true);
      setTimeout(() => {
        // Reset after successful import
        setUploadedFile(null);
        setParsedData([]);
        setSuccess(false);
      }, 2000);
    }
  };

  const handleClear = () => {
    setUploadedFile(null);
    setParsedData([]);
    setError(null);
    setSuccess(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-5 w-5" />
          Import Inventory Data
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* CSV Format Guide */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm">
          <h4 className="font-medium text-blue-900 mb-2">CSV Format:</h4>
          <code className="text-xs text-blue-800 block bg-blue-100 p-2 rounded break-all">
            produce_id,name,quantity,supplier,price,category
          </code>
          <p className="text-xs text-blue-700 mt-2 break-words">
            Example: 1,Red Apples,150,Fresh Farms,2.99,Fruits
          </p>
        </div>

        {/* Upload Area */}
        <div
          className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
            isDragging 
              ? 'border-green-500 bg-green-50' 
              : 'border-gray-300 bg-gray-50 hover:border-green-400'
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleFileSelect}
            className="hidden"
            id="csv-upload"
          />
          
          {!uploadedFile ? (
            <label htmlFor="csv-upload" className="cursor-pointer">
              <Upload className="h-12 w-12 mx-auto mb-3 text-gray-400" />
              <p className="text-sm font-medium mb-1">
                Drop CSV file here or click to browse
              </p>
              <p className="text-xs text-muted-foreground">
                Supports .csv files only
              </p>
            </label>
          ) : (
            <div className="flex items-center justify-between bg-white p-3 rounded">
              <div className="flex items-center gap-2">
                <FileSpreadsheet className="h-5 w-5 text-green-600" />
                <div className="text-left">
                  <p className="text-sm font-medium">{uploadedFile.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {parsedData.length} rows parsed
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClear}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Success Alert */}
        {success && !error && (
          <Alert className="border-green-600 text-green-600">
            <CheckCircle2 className="h-4 w-4" />
            <AlertDescription>
              Successfully parsed {parsedData.length} items!
            </AlertDescription>
          </Alert>
        )}

        {/* Preview Data */}
        {parsedData.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Preview ({parsedData.length} items)</h4>
            <div className="max-h-48 overflow-y-auto space-y-1 bg-gray-50 rounded-lg p-2">
              {parsedData.slice(0, 10).map((item, index) => (
                <div key={index} className="flex items-center justify-between text-xs bg-white p-2 rounded">
                  <div>
                    <span className="font-medium">{item.name}</span>
                    {item.category && (
                      <Badge variant="outline" className="ml-2 text-xs">
                        {item.category}
                      </Badge>
                    )}
                  </div>
                  <span className="text-muted-foreground">Qty: {item.quantity}</span>
                </div>
              ))}
              {parsedData.length > 10 && (
                <p className="text-xs text-center text-muted-foreground py-1">
                  + {parsedData.length - 10} more items
                </p>
              )}
            </div>
          </div>
        )}

        {/* Import Button */}
        <Button 
          onClick={handleImport}
          disabled={parsedData.length === 0}
          className="w-full"
        >
          <Database className="h-4 w-4 mr-2" />
          Import to Database
        </Button>

        {/* Database Connection Note */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-xs text-gray-600">
          <p className="font-medium mb-1">💡 Supabase Integration Ready</p>
          <p>
            When you connect Supabase, imported data will automatically sync to your database.
            Currently running in local mode.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}