from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from collections import defaultdict
from pprint import pprint
from app.db import client as db_client
from app.models.project_schemas import ProjectCreate, ProjectUpdate, ProjectOut, ProjectWithGenerations, GenerationGroup
from app.models.schemas import GenerationJobOut

logger = logging.getLogger(__name__)


class ProjectService:
    """Service for managing user projects and their associated generations."""
    
    @staticmethod
    async def create_project(user_id: str, project_data: ProjectCreate) -> ProjectOut:
        """Create a new project for a user."""
        if db_client.prisma is None:
            await db_client.connect()
        
        project = await db_client.prisma.project.create(
            data={
                "userId": user_id,
                "name": project_data.name,
                "description": project_data.description,
                "referenceImage": project_data.referenceImage,
                "prompt": project_data.prompt,
                "room_type": project_data.room_type,
                "style_preset": project_data.style_preset,
            }
        )
        
        return ProjectOut(
            id=project.id,
            userId=project.userId,
            name=project.name,
            description=project.description,
            isActive=project.isActive,
            referenceImage=project.referenceImage,
            prompt=project.prompt,
            room_type=project.room_type,
            style_preset=project.style_preset,
            createdAt=project.createdAt,
            updatedAt=project.updatedAt,
            generationCount=0,
            generations=[]
        )
    
    @staticmethod
    async def get_user_projects(
        user_id: str, 
        skip: int = 0, 
        limit: int = 20,
        include_inactive: bool = False
    ) -> List[ProjectOut]:
        """Get all projects for a user with generations and generation counts."""
        if db_client.prisma is None:
            await db_client.connect()
        
        where_clause = {"userId": user_id}
        if not include_inactive:
            where_clause["isActive"] = True

        projects = await db_client.prisma.project.find_many(
            where=where_clause,
            skip=skip,
                take=limit,
                include={
                    "generations": {
                        "where": {"status": "done"},
                        "orderBy": {"createdAt": "desc"}
                    }
                }
            )

        result = []
        for project in projects:
            # Get total generation count (including non-done ones) for accurate count

            # pprint(f"Project generations value: {project.generations}")
            total_generations = await db_client.prisma.generationjob.count(
                where={"projectId": project.id}
            )
                
            # Convert filtered generations to GenerationJobOut format
            generation_jobs = []

            if len(project.generations) > 0:
                for gen in project.generations:
                    generation_job = GenerationJobOut(
                        id=gen.id,
                        status=gen.status,
                        reference=gen.reference,
                        output=gen.output,
                        prompt=gen.prompt,
                        room_type=gen.room_type,
                        style_preset=gen.style_preset,
                        user=gen.userId,
                        project_id=gen.projectId,
                        created_at=gen.createdAt.isoformat() if gen.createdAt else None
                    )
                    generation_jobs.append(generation_job)
            

            # pprint(f"Generations jobs: {generation_jobs}")

            result.append(ProjectOut(
                id=project.id,
                userId=project.userId,
                name=project.name,
                description=project.description,
                isActive=project.isActive,
                referenceImage=project.referenceImage,
                prompt=project.prompt,
                room_type=project.room_type,
                style_preset=project.style_preset,
                createdAt=project.createdAt,
                updatedAt=project.updatedAt,
                generationCount=total_generations,  # Accurate total count
                generations=generation_jobs
                ))

        return result
    
    @staticmethod
    async def get_project_by_id(project_id: str, user_id: str) -> Optional[ProjectOut]:
        """Get a specific project with all its generations grouped by parameters."""
        
        project = await db_client.prisma.project.find_first(
            where={"id": project_id, "userId": user_id},
            include={
                "generations": {
                    "orderBy": {"createdAt": "desc"}
                }
            }
        )
        
        if not project:
            return None

        generations = []
        if project.generations:
            for gen in project.generations:
                generation_job = GenerationJobOut(
                    id=gen.id,
                    status=gen.status,
                    reference=gen.reference,
                    output=gen.output,
                    prompt=gen.prompt,
                    room_type=gen.room_type,
                    style_preset=gen.style_preset,
                    user=gen.userId,
                    project_id=gen.projectId,
                    created_at=gen.createdAt.isoformat() if gen.createdAt else None
                )
                generations.append(generation_job)
        
        return ProjectOut(
            id=project.id,
            userId=project.userId,
            name=project.name,
            description=project.description,
            isActive=project.isActive,
            referenceImage=project.referenceImage,
            prompt=project.prompt,
            room_type=project.room_type,
            style_preset=project.style_preset,
            createdAt=project.createdAt,
            updatedAt=project.updatedAt,
            generationCount=len(project.generations) if project.generations else 0,
            generations=generations
        )
    
    @staticmethod
    async def update_project(
        project_id: str, 
        user_id: str, 
        update_data: ProjectUpdate
    ) -> Optional[ProjectOut]:
        """Update a project's details."""
        if db_client.prisma is None:
            await db_client.connect()
        
        # Check if project exists and belongs to user
        existing_project = await db_client.prisma.project.find_first(
            where={"id": project_id, "userId": user_id}
        )
        
        if not existing_project:
            return None
        
        # Build update data, excluding None values
        update_dict = {}
        if update_data.name is not None:
            update_dict["name"] = update_data.name
        if update_data.description is not None:
            update_dict["description"] = update_data.description
        if update_data.isActive is not None:
            update_dict["isActive"] = update_data.isActive
        if update_data.referenceImage is not None:
            update_dict["referenceImage"] = update_data.referenceImage
        if update_data.prompt is not None:
            update_dict["prompt"] = update_data.prompt
        if update_data.room_type is not None:
            update_dict["room_type"] = update_data.room_type
        if update_data.style_preset is not None:
            update_dict["style_preset"] = update_data.style_preset
        
        if not update_dict:
            # No updates to make, return existing project
            return ProjectOut(
                id=existing_project.id,
                userId=existing_project.userId,
                name=existing_project.name,
                description=existing_project.description,
                isActive=existing_project.isActive,
                referenceImage=existing_project.referenceImage,
                prompt=existing_project.prompt,
                room_type=existing_project.room_type,
                style_preset=existing_project.style_preset,
                createdAt=existing_project.createdAt,
                updatedAt=existing_project.updatedAt,
                generationCount=0,  # We'd need a separate query to get this
                generations=project.generations
            )
        
        project = await db_client.prisma.project.update(
            where={"id": project_id},
            data=update_dict,
            include={"_count": {"select": {"generations": True}}}
        )
        
        return ProjectOut(
            id=project.id,
            userId=project.userId,
            name=project.name,
            description=project.description,
            isActive=project.isActive,
            referenceImage=project.referenceImage,
            prompt=project.prompt,
            room_type=project.room_type,
            style_preset=project.style_preset,
            createdAt=project.createdAt,
            updatedAt=project.updatedAt,
            generationCount=project._count.generations if hasattr(project, '_count') else 0,
            generations=project.generations
        )
    
    @staticmethod
    async def update_project_from_generation(
        project_id: str,
        reference_image: str,
        prompt: Optional[str] = None,
        room_type: Optional[str] = None,
        style_preset: Optional[str] = None
    ) -> bool:
        """Update project parameters based on a new generation."""
        if db_client.prisma is None:
            await db_client.connect()
        
        try:
            # logger.info(f"Updating project {project_id} with parameters: reference_image, prompt={prompt}, room_type={room_type}, style_preset={style_preset}")
            
            # First check if project exists
            existing_project = await db_client.prisma.project.find_unique(
                where={"id": project_id}
            )
            
            if not existing_project:
                logger.error(f"Project {project_id} not found")
                return False
            
            await db_client.prisma.project.update(
                where={"id": project_id},
                data={
                    "referenceImage": reference_image,
                    "prompt": prompt,
                    "room_type": room_type,
                    "style_preset": style_preset,
                }
            )
            # await db_client.prisma.project.update(
            #     where={"id": project_id},
            #     data=data
            # )
            logger.info(f"Successfully updated project {project_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update project {project_id} from generation: {str(e)}")
            return False
    
    @staticmethod
    async def delete_project(project_id: str, user_id: str) -> bool:
        """Delete a project. This will set associated generations' projectId to null."""
        if db_client.prisma is None:
            await db_client.connect()
        
        # Check if project exists and belongs to user
        existing_project = await db_client.prisma.project.find_first(
            where={"id": project_id, "userId": user_id}
        )
        
        if not existing_project:
            return False
        
        # Delete the project (cascade will handle the generations relationship)
        await db_client.prisma.project.delete(
            where={"id": project_id}
        )
        
        return True
    
    @staticmethod
    async def add_generation_to_project(
        project_id: str, 
        generation_id: str, 
        user_id: str
    ) -> bool:
        """Associate an existing generation with a project."""
        if db_client.prisma is None:
            await db_client.connect()
        
        # Verify project belongs to user
        project = await db_client.prisma.project.find_first(
            where={"id": project_id, "userId": user_id}
        )
        
        if not project:
            logger.warning(f"Project {project_id} not found")
            return False
        
        # Verify generation belongs to user (or is anonymous)
        generation = await db_client.prisma.generationjob.find_first(
            where={
                "id": generation_id,
                "OR": [
                    {"userId": user_id},
                    {"userId": None}  # Allow anonymous generations to be added
                ]
            }
        )
        
        if not generation:
            logger.warning(f"Generation {generation_id} not found")
            return False
        
        # Update generation to associate with project using relation connect
        await db_client.prisma.generationjob.update(
            where={"id": generation_id},
            data={"project": {"connect": {"id": project_id}}}
        )
        
        # Update project parameters from the generation
        await ProjectService.update_project_from_generation(
            project_id,
            generation.reference,
            generation.prompt,
            generation.room_type,
            generation.style_preset
        )
        
        return True
    
    @staticmethod
    async def remove_generation_from_project(
        generation_id: str, 
        user_id: str
    ) -> bool:
        """Remove a generation from its project."""
        if db_client.prisma is None:
            await db_client.connect()
        
        # Verify generation belongs to user
        generation = await db_client.prisma.generationjob.find_first(
            where={"id": generation_id, "userId": user_id}
        )
        
        if not generation:
            return False
        
        # Remove project association
        await db_client.prisma.generationjob.update(
            where={"id": generation_id},
            data={"projectId": None}
        )
        
        return True
