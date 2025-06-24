package com.example.project.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;

/**
 * Entity representing a project milestone.
 */
@Entity
@Table(name = "milestone")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Milestone {

    /**
     * Unique identifier for the milestone.
     */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /**
     * Title of the milestone.
     */
    @Column(nullable = false, length = 255)
    private String title;

    /**
     * Description of the milestone.
     */
    @Column(length = 1000)
    private String description;

    /**
     * Start date of the milestone.
     */
    @Column(name = "start_date")
    private LocalDate startDate;

    /**
     * Due date of the milestone.
     */
    @Column(name = "due_date")
    private LocalDate dueDate;

    /**
     * State of the milestone (e.g., OPEN, CLOSED).
     */
    @Column(nullable = false, length = 50)
    private String state;

    /**
     * Associated project ID.
     */
    @Column(name = "project_id", nullable = false)
    private Long projectId;

    /**
     * Associated group ID.
     */
    @Column(name = "group_id")
    private Long groupId;
}
