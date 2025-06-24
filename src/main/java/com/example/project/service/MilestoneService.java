package com.example.project.service;

import com.example.project.entity.Milestone;
import com.example.project.entity.Release;
import com.example.project.exception.ResourceNotFoundException;
import com.example.project.exception.ValidationException;
import com.example.project.repository.MilestoneRepository;
import com.example.project.repository.ReleaseRepository;
import com.example.project.utility.ValidationUtil;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class MilestoneService {
    private final MilestoneRepository milestoneRepository;
    private final ValidationUtil validationUtil;

    @Transactional
    public Milestone createMilestone(Milestone milestone) {
        validationUtil.validateMilestone(milestone);
        // Business rule: Milestone name must be unique
        if (milestoneRepository.existsByName(milestone.getName())) {
            throw new ValidationException("Milestone name must be unique");
        }
        // Business rule: Due date must be in the future
        if (milestone.getDueDate() != null && milestone.getDueDate().isBefore(LocalDate.now())) {
            throw new ValidationException("Milestone due date must be in the future");
        }
        milestone.setState(Milestone.State.CREATED);
        return milestoneRepository.save(milestone);
    }

    public Milestone getMilestoneById(String milestoneId) {
        return milestoneRepository.findById(milestoneId)
                .orElseThrow(() -> new ResourceNotFoundException("Milestone not found with id: " + milestoneId));
    }

    @Transactional
    public Milestone updateMilestoneState(String milestoneId, Milestone.State newState) {
        Milestone milestone = getMilestoneById(milestoneId);
        // Business rule: Only allow state transitions from CREATED to IN_PROGRESS, IN_PROGRESS to COMPLETED
        if (milestone.getState() == Milestone.State.CREATED && newState == Milestone.State.IN_PROGRESS) {
            milestone.setState(newState);
        } else if (milestone.getState() == Milestone.State.IN_PROGRESS && newState == Milestone.State.COMPLETED) {
            milestone.setState(newState);
        } else {
            throw new ValidationException("Invalid state transition");
        }
        return milestoneRepository.save(milestone);
    }
}