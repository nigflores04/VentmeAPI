-- CreateTable
CREATE TABLE "Moodboard" (
    "id" TEXT NOT NULL,
    "projectId" TEXT NOT NULL,
    "userId" TEXT,
    "referenceImage" TEXT NOT NULL,
    "prompt" TEXT,
    "style" TEXT,
    "colorPalette" TEXT,
    "status" TEXT NOT NULL,
    "items" TEXT NOT NULL,
    "output" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Moodboard_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "Moodboard" ADD CONSTRAINT "Moodboard_projectId_fkey" FOREIGN KEY ("projectId") REFERENCES "Project"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Moodboard" ADD CONSTRAINT "Moodboard_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE SET NULL ON UPDATE CASCADE;
