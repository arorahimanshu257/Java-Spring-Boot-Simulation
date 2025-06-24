package com.example.project.service;

import com.example.project.dto.*;
import com.example.project.entity.Milestone;
import com.example.project.entity.Release;
import com.example.project.exception.EntityNotFoundException;
import com.example.project.exception.ValidationException;
import com.example.project.repository.MilestoneRepository;
import com.example.project.repository.ReleaseRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class MilestoneServiceImpl implements MilestoneService {

    private final MilestoneRepository milestoneRepository;
    private final ReleaseRepository releaseRepository;

    @Override
    @Transactional
    public MilestoneResponseDTO createMilestone(MilestoneRequestDTO requestDTO) {
        if (milestoneRepository.existsByName(requestDTO.getName())) {
            throw new ValidationException("Milestone name already exists");
        }
        Set<Release> releases = new HashSet<>();
        if (requestDTO.getReleaseIds() != null && !requestDTO.getReleaseIds().isEmpty()) {
            releases = new HashSet<>(releaseRepository.findAllById(requestDTO.getReleaseIds()));
            if (releases.size() != requestDTO.getReleaseIds().size()) {
                throw new EntityNotFoundException("One or more releases not found");
            }
        }
        Milestone milestone = Milestone.builder()
                .name(requestDTO.getName())
                .description(requestDTO.getDescription())
                .dueDate(requestDTO.getDueDate())
                .releases(releases)
                .build();
        Milestone saved = milestoneRepository.save(milestone);
        return toResponseDTO(saved);
    }

    @Override
    @Transactional(readOnly = true)
    public MilestoneResponseDTO getMilestoneById(Long id) {
        Milestone milestone = milestoneRepository.findById(id)
                .orElseThrow(() -> new EntityNotFoundException("Milestone not found"));
        return toResponseDTO(milestone);
    }

    @Override
    @Transactional(readOnly = true)
    public List<MilestoneResponseDTO> getAllMilestones() {
        return milestoneRepository.findAll().stream()
                .map(this::toResponseDTO)
                .collect(Collectors.toList());
    }

    @Override
    @Transactional
    public MilestoneResponseDTO associateReleases(Long milestoneId, List<Long> releaseIds) {
        Milestone milestone = milestoneRepository.findById(milestoneId)
                .orElseThrow(() -> new EntityNotFoundException("Milestone not found"));
        Set<Release> releases = new HashSet<>(releaseRepository.findAllById(releaseIds));
        if (releases.size() != releaseIds.size()) {
            throw new EntityNotFoundException("One or more releases not found");
        }
        milestone.setReleases(releases);
        Milestone saved = milestoneRepository.save(milestone);
        return toResponseDTO(saved);
    }

    @Override
    @Transactional
    public void deleteMilestone(Long id) {
        if (!milestoneRepository.existsById(id)) {
            throw new EntityNotFoundException("Milestone not found");
        }
        milestoneRepository.deleteById(id);
    }

    private MilestoneResponseDTO toResponseDTO(Milestone milestone) {
        MilestoneResponseDTO dto = new MilestoneResponseDTO();
        dto.setId(milestone.getId());
        dto.setName(milestone.getName());
        dto.setDescription(milestone.getDescription());
        dto.setDueDate(milestone.getDueDate());
        dto.setCreatedAt(milestone.getCreatedAt());
        dto.setUpdatedAt(milestone.getUpdatedAt());
        if (milestone.getReleases() != null) {
            Set<ReleaseSummaryDTO> releases = milestone.getReleases().stream()
                    .map(r -> {
                        ReleaseSummaryDTO rs = new ReleaseSummaryDTO();
                        rs.setId(r.getId());
                        rs.setVersion(r.getVersion());
                        rs.setReleaseDate(r.getReleaseDate());
                        return rs;
                    })
                    .collect(Collectors.toSet());
            dto.setReleases(releases);
        }
        return dto;
    }
}
