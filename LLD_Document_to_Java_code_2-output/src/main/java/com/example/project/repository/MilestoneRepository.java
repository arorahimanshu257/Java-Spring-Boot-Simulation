package com.example.project.repository;

import com.example.project.entity.Milestone;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface MilestoneRepository extends MongoRepository<Milestone, String> {
    // Find milestone by title and projectId
    Optional<Milestone> findByTitleAndProjectId(String title, String projectId);

    // Find milestone by title and groupId (if applicable)
    Optional<Milestone> findByTitleAndGroupId(String title, String groupId);
}
