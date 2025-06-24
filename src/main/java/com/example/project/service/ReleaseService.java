package com.example.project.service;

import com.example.project.entity.Release;
import com.example.project.entity.Milestone;
import com.example.project.exception.ResourceNotFoundException;
import com.example.project.exception.ValidationException;
import com.example.project.repository.ReleaseRepository;
import com.example.project.repository.MilestoneRepository;
import com.example.project.utility.ValidationUtil;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class ReleaseService {
    private final ReleaseRepository releaseRepository;
    private final MilestoneRepository milestoneRepository;
    private final ValidationUtil validationUtil;

    @Transactional
    public Release createRelease(Release release) {
        validationUtil.validateRelease(release);
        // Business rule: Release version must be unique
        if (releaseRepository.existsByVersion(release.getVersion())) {
            throw new ValidationException("Release version must be unique");
        }
        return releaseRepository.save(release);
    }

    @Transactional
    public Release associateReleaseToMilestone(String releaseId, String milestoneId) {
        Release release = releaseRepository.findById(releaseId)
                .orElseThrow(() -> new ResourceNotFoundException("Release not found with id: " + releaseId));
        Milestone milestone = milestoneRepository.findById(milestoneId)
                .orElseThrow(() -> new ResourceNotFoundException("Milestone not found with id: " + milestoneId));
        // Business rule: Only allow association if milestone is IN_PROGRESS
        if (milestone.getState() != Milestone.State.IN_PROGRESS) {
            throw new ValidationException("Milestone must be IN_PROGRESS to associate a release");
        }
        release.setMilestone(milestone);
        return releaseRepository.save(release);
    }
}