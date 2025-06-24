package com.example.project.repository;

import com.example.project.entity.Release;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface ReleaseRepository extends MongoRepository<Release, String> {
    // Find release by tag and projectId
    Optional<Release> findByTagAndProjectId(String tag, String projectId);
}
