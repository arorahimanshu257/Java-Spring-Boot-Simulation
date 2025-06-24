package com.example.project.service;

import com.example.project.dto.ReleaseRequestDTO;
import com.example.project.dto.ReleaseResponseDTO;
import com.example.project.entity.Release;
import com.example.project.exception.EntityNotFoundException;
import com.example.project.exception.ValidationException;
import com.example.project.repository.ReleaseRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class ReleaseServiceImpl implements ReleaseService {

    private final ReleaseRepository releaseRepository;

    @Override
    @Transactional
    public ReleaseResponseDTO createRelease(ReleaseRequestDTO requestDTO) {
        if (releaseRepository.existsByVersion(requestDTO.getVersion())) {
            throw new ValidationException("Release version already exists");
        }
        Release release = Release.builder()
                .version(requestDTO.getVersion())
                .description(requestDTO.getDescription())
                .releaseDate(requestDTO.getReleaseDate())
                .milestones(new HashSet<>())
                .build();
        Release saved = releaseRepository.save(release);
        return toResponseDTO(saved);
    }

    @Override
    @Transactional(readOnly = true)
    public ReleaseResponseDTO getReleaseById(Long id) {
        Release release = releaseRepository.findById(id)
                .orElseThrow(() -> new EntityNotFoundException("Release not found"));
        return toResponseDTO(release);
    }

    @Override
    @Transactional(readOnly = true)
    public List<ReleaseResponseDTO> getAllReleases() {
        return releaseRepository.findAll().stream()
                .map(this::toResponseDTO)
                .collect(Collectors.toList());
    }

    @Override
    @Transactional
    public void deleteRelease(Long id) {
        if (!releaseRepository.existsById(id)) {
            throw new EntityNotFoundException("Release not found");
        }
        releaseRepository.deleteById(id);
    }

    private ReleaseResponseDTO toResponseDTO(Release release) {
        ReleaseResponseDTO dto = new ReleaseResponseDTO();
        dto.setId(release.getId());
        dto.setVersion(release.getVersion());
        dto.setDescription(release.getDescription());
        dto.setReleaseDate(release.getReleaseDate());
        dto.setCreatedAt(release.getCreatedAt());
        dto.setUpdatedAt(release.getUpdatedAt());
        if (release.getMilestones() != null) {
            Set<Long> milestoneIds = release.getMilestones().stream()
                    .map(m -> m.getId())
                    .collect(Collectors.toSet());
            dto.setMilestoneIds(milestoneIds);
        }
        return dto;
    }
}
