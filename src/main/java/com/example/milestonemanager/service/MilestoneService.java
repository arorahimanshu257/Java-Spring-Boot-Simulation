package com.example.milestonemanager.service;

import com.example.milestonemanager.dto.MilestoneCreateRequest;
import com.example.milestonemanager.dto.MilestoneResponse;
import com.example.milestonemanager.entity.Milestone;
import com.example.milestonemanager.exception.DuplicateMilestoneTitleException;
import com.example.milestonemanager.exception.InvalidDateRangeException;
import com.example.milestonemanager.repository.MilestoneRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class MilestoneService {
    private final MilestoneRepository milestoneRepository;

    @Transactional
    public MilestoneResponse createMilestone(MilestoneCreateRequest request) {
        // Unique title validation (project or group)
        if (request.getProjectId() != null && milestoneRepository.findByTitleAndProjectId(request.getTitle(), request.getProjectId()).isPresent()) {
            throw new DuplicateMilestoneTitleException("Milestone title must be unique within the project.");
        }
        if (request.getGroupId() != null && milestoneRepository.findByTitleAndGroupId(request.getTitle(), request.getGroupId()).isPresent()) {
            throw new DuplicateMilestoneTitleException("Milestone title must be unique within the group.");
        }
        // Date range validation
        if (request.getStartDate().isAfter(request.getDueDate())) {
            throw new InvalidDateRangeException("Milestone startDate must be before or equal to dueDate.");
        }
        Milestone milestone = Milestone.builder()
                .title(request.getTitle())
                .description(request.getDescription())
                .startDate(request.getStartDate())
                .dueDate(request.getDueDate())
                .state(request.getState())
                .projectId(request.getProjectId())
                .groupId(request.getGroupId())
                .build();
        milestone = milestoneRepository.save(milestone);
        return MilestoneResponse.builder()
                .id(milestone.getId())
                .title(milestone.getTitle())
                .description(milestone.getDescription())
                .startDate(milestone.getStartDate())
                .dueDate(milestone.getDueDate())
                .state(milestone.getState())
                .projectId(milestone.getProjectId())
                .groupId(milestone.getGroupId())
                .build();
    }
}