-- Add output field to moodboard table for storing generated moodboard image URLs
ALTER TABLE "Moodboard" ADD COLUMN "output" TEXT;

-- Add comment to describe the field
COMMENT ON COLUMN "Moodboard"."output" IS 'S3 URL of the generated moodboard image';
