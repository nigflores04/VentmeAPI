/*
  Warnings:

  - You are about to drop the column `paystackPaymentId` on the `Payment` table. All the data in the column will be lost.
  - You are about to drop the `RemodelJob` table. If the table is not empty, all the data it contains will be lost.
  - A unique constraint covering the columns `[payment_reference]` on the table `Payment` will be added. If there are existing duplicate values, this will fail.
  - Added the required column `description` to the `Payment` table without a default value. This is not possible if the table is not empty.
  - Added the required column `payment_reference` to the `Payment` table without a default value. This is not possible if the table is not empty.

*/
-- DropForeignKey
ALTER TABLE "RemodelJob" DROP CONSTRAINT "RemodelJob_userId_fkey";

-- DropIndex
DROP INDEX "Payment_paystackPaymentId_key";

-- AlterTable
ALTER TABLE "Payment" DROP COLUMN "paystackPaymentId",
ADD COLUMN     "description" TEXT NOT NULL,
ADD COLUMN     "isSubscription" BOOLEAN NOT NULL DEFAULT false,
ADD COLUMN     "payment_reference" TEXT NOT NULL,
ADD COLUMN     "subscriptionId" TEXT,
ALTER COLUMN "plan" DROP NOT NULL;

-- DropTable
DROP TABLE "RemodelJob";

-- CreateTable
CREATE TABLE "GenerationJob" (
    "id" TEXT NOT NULL,
    "userId" TEXT,
    "status" TEXT NOT NULL,
    "reference" TEXT NOT NULL,
    "prompt" TEXT,
    "room_type" TEXT,
    "style_preset" TEXT,
    "width" INTEGER NOT NULL,
    "height" INTEGER NOT NULL,
    "output" TEXT,
    "error" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "GenerationJob_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Subscription" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "plan" TEXT NOT NULL,
    "planCode" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "nextPaymentDate" TIMESTAMP(3),
    "lastPaymentDate" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Subscription_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "Payment_payment_reference_key" ON "Payment"("payment_reference");

-- AddForeignKey
ALTER TABLE "GenerationJob" ADD CONSTRAINT "GenerationJob_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Payment" ADD CONSTRAINT "Payment_subscriptionId_fkey" FOREIGN KEY ("subscriptionId") REFERENCES "Subscription"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Subscription" ADD CONSTRAINT "Subscription_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
