package com.example.project.service;

import com.example.project.entity.Release;
import com.example.project.entity.Milestone;
import com.example.project.exception.ResourceNotFoundException;

public interface AssociationService {
    void associateReleaseToMilestone(String releaseId, String milestoneId) throws ResourceNotFoundException;
    void removeReleaseFromMilestone(String releaseId, String milestoneId) throws ResourceNotFoundException;
    Milestone getMilestoneForRelease(String releaseId) throws ResourceNotFoundException;
}