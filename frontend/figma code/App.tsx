import { useState } from "react";
import { ProduceImageViewer } from "./components/ProduceImageViewer";
import { CSVImporter } from "./components/CSVImporter";
import { ProduceList } from "./components/ProduceList";
import { Button } from "./components/ui/button";
import { Badge } from "./components/ui/badge";
import { 
  Menu, 
  X, 
  Apple, 
  Shield,
  Activity,
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

export default function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [selectedProduceId, setSelectedProduceId] = useState<string | null>("1");
  const [produceItems, setProduceItems] = useState<ProduceItem[]>([
    {
      id: "1",
      name: "Red Apples",
      category: "Fruits",
      image_url: "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=800",
      status: "good",
      confidence: 92,
      last_checked: new Date(Date.now() - 1000 * 60 * 30),
      quantity: 150,
      supplier: "Fresh Farms Co.",
      price: 2.99,
      detections: [
        {
          id: "d1",
          label: "Apple - Good Quality",
          confidence: 95,
          boundingBox: { x: 20, y: 15, width: 25, height: 30 },
          status: "good"
        },
        {
          id: "d2",
          label: "Apple - Good Quality",
          confidence: 92,
          boundingBox: { x: 55, y: 20, width: 30, height: 35 },
          status: "good"
        },
        {
          id: "d3",
          label: "Apple - Minor Bruising",
          confidence: 78,
          boundingBox: { x: 15, y: 55, width: 28, height: 32 },
          status: "warning"
        }
      ]
    },
    {
      id: "2",
      name: "Bananas",
      category: "Fruits",
      image_url: "https://images.unsplash.com/photo-1603833665858-e61d17a86224?w=800",
      status: "warning",
      confidence: 76,
      last_checked: new Date(Date.now() - 1000 * 60 * 60 * 2),
      quantity: 200,
      supplier: "Tropical Imports",
      price: 1.49,
      detections: [
        {
          id: "d4",
          label: "Banana - Overripe",
          confidence: 88,
          boundingBox: { x: 30, y: 25, width: 40, height: 45 },
          status: "warning"
        },
        {
          id: "d5",
          label: "Banana - Good Quality",
          confidence: 81,
          boundingBox: { x: 50, y: 60, width: 35, height: 30 },
          status: "good"
        }
      ]
    },
    {
      id: "3",
      name: "Tomatoes",
      category: "Vegetables",
      image_url: "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=800",
      status: "good",
      confidence: 89,
      last_checked: new Date(Date.now() - 1000 * 60 * 45),
      quantity: 180,
      supplier: "Valley Vegetables",
      price: 3.49,
      detections: [
        {
          id: "d6",
          label: "Tomato - Fresh",
          confidence: 94,
          boundingBox: { x: 25, y: 30, width: 30, height: 30 },
          status: "good"
        },
        {
          id: "d7",
          label: "Tomato - Fresh",
          confidence: 91,
          boundingBox: { x: 60, y: 35, width: 28, height: 28 },
          status: "good"
        },
        {
          id: "d8",
          label: "Tomato - Fresh",
          confidence: 85,
          boundingBox: { x: 40, y: 65, width: 32, height: 30 },
          status: "good"
        }
      ]
    },
    {
      id: "4",
      name: "Lettuce",
      category: "Vegetables",
      image_url: "https://images.unsplash.com/photo-1622206151226-18ca2c9ab4a1?w=800",
      status: "bad",
      confidence: 91,
      last_checked: new Date(Date.now() - 1000 * 60 * 15),
      quantity: 75,
      supplier: "Green Leaf Farms",
      price: 2.29,
      detections: [
        {
          id: "d9",
          label: "Lettuce - Wilted",
          confidence: 93,
          boundingBox: { x: 35, y: 40, width: 35, height: 40 },
          status: "bad"
        }
      ]
    },
    {
      id: "5",
      name: "Oranges",
      category: "Fruits",
      image_url: "https://images.unsplash.com/photo-1580052614034-c55d20bfee3b?w=800",
      status: "good",
      confidence: 94,
      last_checked: new Date(Date.now() - 1000 * 60 * 60),
      quantity: 220,
      supplier: "Citrus Grove Ltd.",
      price: 4.99
    }
  ]);

  const selectedProduce = produceItems.find(p => p.id === selectedProduceId) || produceItems[0];

  const handleProduceSelect = (produceId: string) => {
    setSelectedProduceId(produceId);
  };

  const handleCSVImport = (data: InventoryData[]) => {
    // When Supabase is connected, this will insert into the database
    // For now, update local state
    console.log("CSV Import data:", data);
    
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
                <Apple className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Produce Quality Management</h1>
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
            <CSVImporter onImport={handleCSVImport} />
          </div>
        </aside>

        {/* Mobile sidebar */}
        {isSidebarOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <div className="fixed inset-0 bg-black/50" onClick={() => setIsSidebarOpen(false)} />
            <aside className="fixed left-0 top-0 bottom-0 w-80 bg-white overflow-y-auto">
              <div className="p-4">
                <CSVImporter onImport={handleCSVImport} />
              </div>
            </aside>
          </div>
        )}

        {/* Main content area - Produce Image Viewer */}
        <main className="flex-1 overflow-y-auto">
          <div className="p-6">
            <div className="max-w-5xl mx-auto">
              <ProduceImageViewer 
                produce={selectedProduce}
                onMLUpdate={handleMLUpdate}
              />
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
