package com.example.project.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Entity representing a release associated with a milestone.
 */
@Entity
@Table(name = "release")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Release {

    /**
     * Unique identifier for the release.
     */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /**
     * Tag for the release (e.g., v1.0.0).
     */
    @Column(nullable = false, length = 100)
    private String tag;

    /**
     * Description of the release.
     */
    @Column(length = 1000)
    private String description;

    /**
     * Associated project ID.
     */
    @Column(name = "project_id", nullable = false)
    private Long projectId;

    /**
     * Associated milestone ID.
     */
    @Column(name = "milestone_id", nullable = false)
    private Long milestoneId;
}
