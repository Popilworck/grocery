# Supabase Integration Guide

## Current CSV Processing Flow

1. **CSV Upload** → User uploads CSV file in left sidebar
2. **Parsing** → `CSVImporter.tsx` parses the CSV into structured data
3. **Callback** → Parsed data sent to `App.tsx` via `onImport()` callback
4. **Local State** → Currently updates `produceItems` state (local only)

---

## What You Need to Do for Supabase Integration

### Step 1: Create Supabase Tables

Run these SQL commands in your Supabase SQL Editor:

```sql
-- Produce items table
CREATE TABLE produce (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  image_url TEXT,
  status TEXT CHECK (status IN ('good', 'bad', 'warning', 'unchecked')),
  confidence NUMERIC DEFAULT 0,
  last_checked TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  quantity INTEGER DEFAULT 0,
  supplier TEXT,
  price NUMERIC,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ML Detection results table
CREATE TABLE detections (
  id TEXT PRIMARY KEY,
  produce_id TEXT REFERENCES produce(id) ON DELETE CASCADE,
  label TEXT NOT NULL,
  confidence NUMERIC NOT NULL,
  bbox_x NUMERIC NOT NULL,
  bbox_y NUMERIC NOT NULL,
  bbox_width NUMERIC NOT NULL,
  bbox_height NUMERIC NOT NULL,
  status TEXT CHECK (status IN ('good', 'bad', 'warning')),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for better query performance
CREATE INDEX idx_produce_status ON produce(status);
CREATE INDEX idx_produce_category ON produce(category);
CREATE INDEX idx_detections_produce_id ON detections(produce_id);
```

### Step 2: Install Supabase Client

```bash
npm install @supabase/supabase-js
```

### Step 3: Create Supabase Client

Create a new file `/lib/supabase.ts`:

```typescript
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'YOUR_SUPABASE_URL';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'YOUR_SUPABASE_ANON_KEY';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
```

### Step 4: Update CSV Import Handler in App.tsx

Replace the `handleCSVImport` function with:

```typescript
const handleCSVImport = async (data: InventoryData[]) => {
  console.log("CSV Import data:", data);
  
  try {
    // Upsert to Supabase (insert new, update existing)
    const produceData = data.map(item => ({
      id: item.produce_id || `produce-${Date.now()}-${Math.random()}`,
      name: item.name,
      category: item.category || "Uncategorized",
      quantity: item.quantity,
      supplier: item.supplier,
      price: item.price,
      status: 'unchecked',
      confidence: 0,
      last_checked: new Date().toISOString()
    }));

    const { data: insertedData, error } = await supabase
      .from('produce')
      .upsert(produceData, { onConflict: 'id' })
      .select();

    if (error) throw error;

    // Refresh local state from database
    await fetchProduceItems();
    
    console.log('Successfully imported to Supabase:', insertedData);
  } catch (error) {
    console.error('Error importing to Supabase:', error);
    // Optionally show error to user
  }
};
```

### Step 5: Fetch Data from Supabase

Add this function to load data from database:

```typescript
const fetchProduceItems = async () => {
  try {
    const { data, error } = await supabase
      .from('produce')
      .select(`
        *,
        detections (*)
      `)
      .order('created_at', { ascending: false });

    if (error) throw error;

    // Transform Supabase data to match ProduceItem interface
    const items: ProduceItem[] = data.map(item => ({
      id: item.id,
      name: item.name,
      category: item.category,
      image_url: item.image_url || "https://images.unsplash.com/photo-1610832958506-aa56368176cf?w=800",
      status: item.status as 'good' | 'bad' | 'warning' | 'unchecked',
      confidence: item.confidence,
      last_checked: new Date(item.last_checked),
      quantity: item.quantity,
      supplier: item.supplier,
      price: item.price,
      detections: item.detections?.map((d: any) => ({
        id: d.id,
        label: d.label,
        confidence: d.confidence,
        boundingBox: {
          x: d.bbox_x,
          y: d.bbox_y,
          width: d.bbox_width,
          height: d.bbox_height
        },
        status: d.status
      }))
    }));

    setProduceItems(items);
  } catch (error) {
    console.error('Error fetching produce items:', error);
  }
};
```

### Step 6: Update ML Results Handler

Update `handleMLUpdate` to save to Supabase:

```typescript
const handleMLUpdate = async (produceId: string, detections: Detection[]) => {
  try {
    // Calculate overall status
    const badCount = detections.filter(d => d.status === 'bad').length;
    const warningCount = detections.filter(d => d.status === 'warning').length;
    const totalCount = detections.length;
    
    let status: 'good' | 'bad' | 'warning' = 'good';
    if (badCount > totalCount / 2) status = 'bad';
    else if (warningCount > 0 || badCount > 0) status = 'warning';
    
    const avgConfidence = detections.reduce((sum, d) => sum + d.confidence, 0) / totalCount;

    // Update produce status in Supabase
    const { error: produceError } = await supabase
      .from('produce')
      .update({
        status,
        confidence: avgConfidence,
        last_checked: new Date().toISOString()
      })
      .eq('id', produceId);

    if (produceError) throw produceError;

    // Delete old detections
    await supabase
      .from('detections')
      .delete()
      .eq('produce_id', produceId);

    // Insert new detections
    const detectionsData = detections.map(d => ({
      id: d.id,
      produce_id: produceId,
      label: d.label,
      confidence: d.confidence,
      bbox_x: d.boundingBox.x,
      bbox_y: d.boundingBox.y,
      bbox_width: d.boundingBox.width,
      bbox_height: d.boundingBox.height,
      status: d.status
    }));

    const { error: detectionsError } = await supabase
      .from('detections')
      .insert(detectionsData);

    if (detectionsError) throw detectionsError;

    // Refresh local state
    await fetchProduceItems();
    
  } catch (error) {
    console.error('Error updating ML results:', error);
  }
};
```

### Step 7: Load Data on Mount

Add useEffect to load data when app starts:

```typescript
import { useEffect } from 'react';

// Inside App component
useEffect(() => {
  fetchProduceItems();
}, []);
```

---

## Summary

**Before Supabase:**
- CSV data → Parse → Update local state → Data lost on refresh

**After Supabase:**
- CSV data → Parse → Insert to Supabase → Persist forever
- ML results → Save to database → Available across devices
- Real-time sync possible with Supabase subscriptions

**Key Benefits:**
- ✅ Data persists across sessions
- ✅ Multiple users can access same data
- ✅ ML results stored permanently
- ✅ Easy to query and filter
- ✅ Built-in authentication and RLS (Row Level Security)

---

## Optional: Real-time Updates

Add real-time subscriptions to see changes live:

```typescript
useEffect(() => {
  const subscription = supabase
    .channel('produce-changes')
    .on('postgres_changes', 
      { event: '*', schema: 'public', table: 'produce' },
      (payload) => {
        console.log('Change received!', payload);
        fetchProduceItems(); // Refresh data
      }
    )
    .subscribe();

  return () => {
    subscription.unsubscribe();
  };
}, []);
```
