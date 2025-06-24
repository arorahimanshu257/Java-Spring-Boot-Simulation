package com.example.project.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.*;
import java.time.LocalDate;

@Entity
@Table(name = "milestone", uniqueConstraints = {
    @UniqueConstraint(columnNames = {"title", "project_id", "group_id"})
})
public class Milestone {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @NotBlank
    @Size(max = 255)
    private String title;

    @Size(max = 1000)
    private String description;

    @NotNull
    private LocalDate startDate;

    @NotNull
    private LocalDate dueDate;

    @NotBlank
    @Size(max = 50)
    private String state;

    @NotNull
    @Column(name = "project_id")
    private Long projectId;

    @Column(name = "group_id")
    private Long groupId;

    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }

    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }

    public LocalDate getStartDate() { return startDate; }
    public void setStartDate(LocalDate startDate) { this.startDate = startDate; }

    public LocalDate getDueDate() { return dueDate; }
    public void setDueDate(LocalDate dueDate) { this.dueDate = dueDate; }

    public String getState() { return state; }
    public void setState(String state) { this.state = state; }

    public Long getProjectId() { return projectId; }
    public void setProjectId(Long projectId) { this.projectId = projectId; }

    public Long getGroupId() { return groupId; }
    public void setGroupId(Long groupId) { this.groupId = groupId; }

    @AssertTrue(message = "Start date must be before or equal to due date")
    public boolean isStartDateBeforeDueDate() {
        if (startDate == null || dueDate == null) return true;
        return !startDate.isAfter(dueDate);
    }
}
