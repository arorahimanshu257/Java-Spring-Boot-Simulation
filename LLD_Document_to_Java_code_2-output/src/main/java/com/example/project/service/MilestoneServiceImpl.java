package com.example.project.service;

import com.example.project.entity.Milestone;
import com.example.project.exception.DuplicateMilestoneTitleException;
import com.example.project.exception.InvalidMilestoneDatesException;
import com.example.project.exception.ResourceNotFoundException;
import com.example.project.repository.MilestoneRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;
import java.util.Optional;

@Service
public class MilestoneServiceImpl implements MilestoneService {

    private final MilestoneRepository milestoneRepository;

    @Autowired
    public MilestoneServiceImpl(MilestoneRepository milestoneRepository) {
        this.milestoneRepository = milestoneRepository;
    }

    @Override
    @Transactional
    public Milestone createMilestone(Milestone milestone) throws DuplicateMilestoneTitleException, InvalidMilestoneDatesException {
        // Validate unique title within project/group
        boolean exists = milestoneRepository.existsByTitleAndProjectId(milestone.getTitle(), milestone.getProjectId());
        if (exists) {
            throw new DuplicateMilestoneTitleException("Milestone title must be unique within the project.");
        }
        // Validate startDate <= dueDate
        if (milestone.getStartDate() != null && milestone.getDueDate() != null && milestone.getStartDate().isAfter(milestone.getDueDate())) {
            throw new InvalidMilestoneDatesException("Milestone startDate must be before or equal to dueDate.");
        }
        return milestoneRepository.save(milestone);
    }

    @Override
    public List<Milestone> getMilestonesByProjectId(String projectId) {
        return milestoneRepository.findByProjectId(projectId);
    }

    @Override
    public Milestone getMilestoneById(String milestoneId) {
        return milestoneRepository.findById(milestoneId)
                .orElseThrow(() -> new ResourceNotFoundException("Milestone not found with id: " + milestoneId));
    }

    @Override
    @Transactional
    public void deleteMilestone(String milestoneId) {
        if (!milestoneRepository.existsById(milestoneId)) {
            throw new ResourceNotFoundException("Milestone not found with id: " + milestoneId);
        }
        milestoneRepository.deleteById(milestoneId);
    }
}
