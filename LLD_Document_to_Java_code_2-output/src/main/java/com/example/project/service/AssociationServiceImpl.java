package com.example.project.service;

import com.example.project.entity.Release;
import com.example.project.entity.Milestone;
import com.example.project.exception.ResourceNotFoundException;
import com.example.project.repository.ReleaseRepository;
import com.example.project.repository.MilestoneRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AssociationServiceImpl implements AssociationService {

    private final ReleaseRepository releaseRepository;
    private final MilestoneRepository milestoneRepository;

    @Autowired
    public AssociationServiceImpl(ReleaseRepository releaseRepository, MilestoneRepository milestoneRepository) {
        this.releaseRepository = releaseRepository;
        this.milestoneRepository = milestoneRepository;
    }

    @Override
    @Transactional
    public void associateReleaseToMilestone(String releaseId, String milestoneId) throws ResourceNotFoundException {
        Release release = releaseRepository.findById(releaseId)
                .orElseThrow(() -> new ResourceNotFoundException("Release not found with id: " + releaseId));
        Milestone milestone = milestoneRepository.findById(milestoneId)
                .orElseThrow(() -> new ResourceNotFoundException("Milestone not found with id: " + milestoneId));
        release.setMilestoneId(milestoneId);
        releaseRepository.save(release);
    }

    @Override
    @Transactional
    public void removeReleaseFromMilestone(String releaseId, String milestoneId) throws ResourceNotFoundException {
        Release release = releaseRepository.findById(releaseId)
                .orElseThrow(() -> new ResourceNotFoundException("Release not found with id: " + releaseId));
        if (!milestoneId.equals(release.getMilestoneId())) {
            throw new ResourceNotFoundException("Release is not associated with the given milestone.");
        }
        release.setMilestoneId(null);
        releaseRepository.save(release);
    }

    @Override
    public Milestone getMilestoneForRelease(String releaseId) throws ResourceNotFoundException {
        Release release = releaseRepository.findById(releaseId)
                .orElseThrow(() -> new ResourceNotFoundException("Release not found with id: " + releaseId));
        String milestoneId = release.getMilestoneId();
        if (milestoneId == null) {
            throw new ResourceNotFoundException("Release is not associated with any milestone.");
        }
        return milestoneRepository.findById(milestoneId)
                .orElseThrow(() -> new ResourceNotFoundException("Milestone not found with id: " + milestoneId));
    }
}
