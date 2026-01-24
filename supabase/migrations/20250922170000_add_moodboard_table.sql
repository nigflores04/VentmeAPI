-- Create Moodboard table
CREATE TABLE IF NOT EXISTS "Moodboard" (
    "id" TEXT NOT NULL,
    "projectId" TEXT NOT NULL,
    "userId" TEXT,
    "referenceImage" TEXT NOT NULL,
    "prompt" TEXT,
    "style" TEXT,
    "colorPalette" TEXT,
    "status" TEXT NOT NULL DEFAULT 'generating',
    "items" TEXT NOT NULL DEFAULT '[]',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Moodboard_pkey" PRIMARY KEY ("id")
);

-- Add foreign key constraints
ALTER TABLE "Moodboard" 
ADD CONSTRAINT "Moodboard_projectId_fkey" 
FOREIGN KEY ("projectId") REFERENCES "Project"("id") 
ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE "Moodboard" 
ADD CONSTRAINT "Moodboard_userId_fkey" 
FOREIGN KEY ("userId") REFERENCES "User"("id") 
ON DELETE SET NULL ON UPDATE CASCADE;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS "Moodboard_projectId_idx" ON "Moodboard"("projectId");
CREATE INDEX IF NOT EXISTS "Moodboard_userId_idx" ON "Moodboard"("userId");
CREATE INDEX IF NOT EXISTS "Moodboard_status_idx" ON "Moodboard"("status");
CREATE INDEX IF NOT EXISTS "Moodboard_createdAt_idx" ON "Moodboard"("createdAt");
