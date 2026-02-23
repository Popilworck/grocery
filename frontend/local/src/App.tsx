import { useEffect, useState } from "react";
import { ProduceImageViewer } from "./components/ProduceImageViewer";
import { CSVImporter } from "./components/CSVImporter";
import { ProduceList } from "./components/ProduceList";
import { Alert, AlertDescription } from "./components/ui/alert";
import { Button } from "./components/ui/button";
import { Badge } from "./components/ui/badge";
import { isSupabaseConfigured, supabase } from "./lib/supabase";
import { 
  Menu, 
  X, 
  Shield,
  Database
} from "lucide-react";

export interface ProduceItem {
  id: string;
  name: string;
  category: string;
  image_url: string;
  status: 'good' | 'bad' | 'warning' | 'unchecked';
  confidence: number;
  last_checked: Date;
  quantity: number;
  supplier?: string;
  price?: number;
  detections?: Detection[];
}

export interface Detection {
  id: string;
  label: string;
  confidence: number;
  boundingBox: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  status: 'good' | 'bad' | 'warning';
}

export interface InventoryData {
  produce_id: string;
  name: string;
  quantity: number;
  supplier?: string;
  price?: number;
  category?: string;
}

type InventoryRow = {
  id: string;
  name: string;
  category?: string | null;
  image_url?: string | null;
  status?: "good" | "bad" | "warning" | "unchecked" | null;
  confidence?: number | null;
  last_checked?: string | null;
  quantity?: number | null;
  supplier?: string | null;
  price?: number | null;
  detections?: unknown;
};

const READ_TABLE_NAME = "produce";
const WRITE_TABLE_NAME = "inventory";
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5001";

const fallbackItems: ProduceItem[] = [];

const parseDetections = (value: unknown): Detection[] | undefined => {
  if (Array.isArray(value)) {
    return value as Detection[];
  }

  if (typeof value === "string" && value.trim().length > 0) {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? (parsed as Detection[]) : undefined;
    } catch {
      return undefined;
    }
  }

  return undefined;
};

const mapRowToItem = (row: InventoryRow): ProduceItem => {
  const lastChecked = row.last_checked ? new Date(row.last_checked) : new Date();

  return {
    id: row.id,
    name: row.name,
    category: row.category ?? "Uncategorized",
    image_url:
      row.image_url ?? "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=800",
    status: row.status ?? "unchecked",
    confidence: row.confidence ?? 0,
    last_checked: lastChecked,
    quantity: row.quantity ?? 0,
    supplier: row.supplier ?? undefined,
    price: row.price ?? undefined,
    detections: parseDetections(row.detections)
  };
};

export default function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [selectedProduceId, setSelectedProduceId] = useState<string | null>("1");
  const [produceItems, setProduceItems] = useState<ProduceItem[]>(fallbackItems);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const selectedProduce =
    produceItems.find(p => p.id === selectedProduceId) || produceItems[0] || null;

  const fetchInventory = async () => {
    if (!supabase) return;

    setIsLoading(true);
    setLoadError(null);

    const { data, error } = await supabase
      .from(READ_TABLE_NAME)
      .select("*")
      .order("name");

    if (error) {
      setLoadError(error.message);
      setIsLoading(false);
      return;
    }

    if (data && data.length > 0) {
      setProduceItems(data.map(mapRowToItem));
    }

    setIsLoading(false);
  };

  useEffect(() => {
    if (!supabase) return;

    fetchInventory();
    const intervalId = window.setInterval(fetchInventory, 60000);

    return () => window.clearInterval(intervalId);
  }, []);

  const handleProduceSelect = (produceId: string) => {
    setSelectedProduceId(produceId);
  };

  const handleCSVImport = async (data: InventoryData[]) => {
    console.log("CSV Import data:", data);

    if (supabase) {
      const payload = data.map((item, index) => ({
        id: item.produce_id || `new-${Date.now()}-${index}`,
        name: item.name,
        category: item.category ?? null,
        quantity: item.quantity,
        supplier: item.supplier ?? null,
        price: item.price ?? null
      }));

      const { error } = await supabase
        .from(WRITE_TABLE_NAME)
        .upsert(payload, { onConflict: "id" });

      if (error) {
        setLoadError(error.message);
        return;
      }

      await fetchInventory();
      return;
    }
    
    // Merge CSV data with existing produce items
    const updatedItems = produceItems.map(item => {
      const csvItem = data.find(d => d.produce_id === item.id || d.name.toLowerCase() === item.name.toLowerCase());
      if (csvItem) {
        return {
          ...item,
          quantity: csvItem.quantity,
          supplier: csvItem.supplier || item.supplier,
          price: csvItem.price || item.price,
          category: csvItem.category || item.category
        };
      }
      return item;
    });

    // Add new items from CSV that don't exist
    const newItems = data
      .filter(csvItem => !produceItems.some(p => p.id === csvItem.produce_id || p.name.toLowerCase() === csvItem.name.toLowerCase()))
      .map((csvItem, index) => ({
        id: csvItem.produce_id || `new-${Date.now()}-${index}`,
        name: csvItem.name,
        category: csvItem.category || "Uncategorized",
        image_url: "https://images.unsplash.com/photo-1610832958506-aa56368176cf?w=800",
        status: "unchecked" as const,
        confidence: 0,
        last_checked: new Date(),
        quantity: csvItem.quantity,
        supplier: csvItem.supplier,
        price: csvItem.price
      }));

    setProduceItems([...updatedItems, ...newItems]);
  };

  const handleCSVUpload = async (file: File) => {
    setLoadError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${BACKEND_URL}/upload-csv`, {
        method: "POST",
        body: formData
      });

      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || `Upload failed (${response.status})`);
      }

      const result = await response.json().catch(() => null);
      if (result?.error) {
        throw new Error(result.error);
      }

      await fetchInventory();
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Failed to upload CSV");
    }
  };

  const handleMLUpdate = (produceId: string, detections: Detection[]) => {
    // When Supabase is connected, this will update the database
    // For now, update local state
    setProduceItems(prev => prev.map(item => {
      if (item.id === produceId) {
        const badCount = detections.filter(d => d.status === 'bad').length;
        const warningCount = detections.filter(d => d.status === 'warning').length;
        const totalCount = detections.length;
        
        let status: 'good' | 'bad' | 'warning' = 'good';
        if (badCount > totalCount / 2) status = 'bad';
        else if (warningCount > 0 || badCount > 0) status = 'warning';
        
        const avgConfidence = detections.reduce((sum, d) => sum + d.confidence, 0) / totalCount;
        
        return {
          ...item,
          detections,
          status,
          confidence: avgConfidence,
          last_checked: new Date()
        };
      }
      return item;
    }));
  };

  const getStatusStats = () => {
    const good = produceItems.filter(p => p.status === 'good').length;
    const warning = produceItems.filter(p => p.status === 'warning').length;
    const bad = produceItems.filter(p => p.status === 'bad').length;
    const unchecked = produceItems.filter(p => p.status === 'unchecked').length;
    return { good, warning, bad, unchecked };
  };

  const stats = getStatusStats();

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-white/20 px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              className="lg:hidden"
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            >
              {isSidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </Button>
            <div className="flex items-center gap-2">
              <div className="p-2 bg-green-100 rounded-lg">
                <img
                  src="/logo.svg"
                  alt="Produce Quality"
                  className="h-5 w-5"
                />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">GroceryWatch</h1>
                <p className="text-sm text-gray-600">ML-Powered Quality Detection</p>
              </div>
            </div>
          </div>
          <div className="hidden sm:flex items-center gap-4">
            <div className="flex items-center gap-3 text-sm">
              <Badge variant="default" className="bg-green-600">
                <Shield className="h-3 w-3 mr-1" />
                {stats.good} Good
              </Badge>
              <Badge variant="default" className="bg-yellow-600">
                {stats.warning} Warning
              </Badge>
              <Badge variant="default" className="bg-red-600">
                {stats.bad} Bad
              </Badge>
            </div>
            <div className="text-sm text-gray-500">
              {new Date().toLocaleString()}
            </div>
          </div>
        </div>
      </header>

      <div className="flex h-[calc(100vh-80px)]">
        {/* Left panel - CSV Import (Desktop) */}
        <aside className="hidden lg:block w-80 bg-white/70 backdrop-blur-sm border-r border-white/20 overflow-y-auto">
          <div className="p-4">
            <CSVImporter onImport={handleCSVImport} onUploadFile={handleCSVUpload} />
          </div>
        </aside>

        {/* Mobile sidebar */}
        {isSidebarOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <div className="fixed inset-0 bg-black/50" onClick={() => setIsSidebarOpen(false)} />
            <aside className="fixed left-0 top-0 bottom-0 w-80 bg-white overflow-y-auto">
              <div className="p-4">
                <CSVImporter onImport={handleCSVImport} onUploadFile={handleCSVUpload} />
              </div>
            </aside>
          </div>
        )}

        {/* Main content area - Produce Image Viewer */}
        <main className="flex-1 overflow-y-auto">
          <div className="p-6">
            <div className="max-w-5xl mx-auto space-y-4">
              {!isSupabaseConfigured && (
                <Alert>
                  <AlertDescription>
                    Supabase is not configured. Add VITE_SUPABASE_URL and
                    VITE_SUPABASE_ANON_KEY to .env and restart the dev server.
                  </AlertDescription>
                </Alert>
              )}
              {loadError && (
                <Alert variant="destructive">
                  <AlertDescription>Failed to load inventory: {loadError}</AlertDescription>
                </Alert>
              )}
              {isLoading && (
                <div className="text-sm text-gray-600">Loading inventory...</div>
              )}
              {selectedProduce ? (
                <ProduceImageViewer
                  produce={selectedProduce}
                  onMLUpdate={handleMLUpdate}
                />
              ) : (
                <div className="rounded-lg border border-dashed p-8 text-center text-sm text-gray-600">
                  No inventory items yet. Import a CSV to get started.
                </div>
              )}
            </div>
          </div>
        </main>

        {/* Right panel - Produce List (Desktop) */}
        <aside className="hidden lg:block w-80 bg-white/70 backdrop-blur-sm border-l border-white/20 overflow-y-auto">
          <div className="p-4">
            <ProduceList
              items={produceItems}
              selectedId={selectedProduceId}
              onSelect={handleProduceSelect}
            />
          </div>
        </aside>
      </div>

      {/* Mobile bottom quick button */}
      <div className="fixed bottom-4 right-4 lg:hidden flex gap-2">
        <Button
          variant="default"
          size="sm"
          onClick={() => setIsSidebarOpen(true)}
          className="bg-green-600 hover:bg-green-700 shadow-lg"
        >
          <Database className="h-4 w-4 mr-2" />
          Import CSV
        </Button>
      </div>
    </div>
  );
}
