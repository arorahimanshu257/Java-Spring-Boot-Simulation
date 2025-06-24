package com.example.milestonemanager.service;

import com.example.milestonemanager.entity.Milestone;
import com.example.milestonemanager.entity.Release;
import com.example.milestonemanager.exception.MilestoneNotFoundException;
import com.example.milestonemanager.exception.ReleaseAlreadyAssociatedException;
import com.example.milestonemanager.exception.ReleaseNotFoundException;
import com.example.milestonemanager.repository.MilestoneRepository;
import com.example.milestonemanager.repository.ReleaseRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class ReleaseService {
    private final ReleaseRepository releaseRepository;
    private final MilestoneRepository milestoneRepository;

    @Transactional
    public void associateReleaseWithMilestone(Long releaseId, Long milestoneId) {
        Release release = releaseRepository.findById(releaseId)
                .orElseThrow(() -> new ReleaseNotFoundException("Release not found with id: " + releaseId));
        Milestone milestone = milestoneRepository.findById(milestoneId)
                .orElseThrow(() -> new MilestoneNotFoundException("Milestone not found with id: " + milestoneId));
        // Check if release is already associated with a milestone
        if (release.getMilestoneId() != null) {
            throw new ReleaseAlreadyAssociatedException("Release is already associated with a milestone.");
        }
        // Associate
        release.setMilestoneId(milestoneId);
        releaseRepository.save(release);
    }
}