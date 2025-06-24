```java
// Java Spring Boot code generated based on LLD

// Controller Class
@RestController
@RequestMapping("/api/v1")
public class ExampleController {

    @Autowired
    private ExampleService exampleService;

    @GetMapping("/example")
    public ResponseEntity<ExampleResponse> getExample() {
        ExampleResponse response = exampleService.getExample();
        return ResponseEntity.ok(response);
    }

    @PostMapping("/example")
    public ResponseEntity<ExampleResponse> createExample(@Valid @RequestBody ExampleRequest request) {
        ExampleResponse response = exampleService.createExample(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }
}

// Service Class
@Service
public class ExampleService {

    public ExampleResponse getExample() {
        // Business logic for getting example
        return new ExampleResponse();
    }

    public ExampleResponse createExample(ExampleRequest request) {
        // Business logic for creating example
        return new ExampleResponse();
    }
}

// Model Classes
@Data
public class ExampleRequest {
    @NotNull
    private String name;
}

@Data
public class ExampleResponse {
    private String id;
    private String name;
}

// Entity Class
@Entity
public class ExampleEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String name;
}

// Repository Interface
public interface ExampleRepository extends JpaRepository<ExampleEntity, Long> {
}

// Exception Handling
@ControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidationExceptions(MethodArgumentNotValidException ex) {
        ErrorResponse errorResponse = new ErrorResponse("Validation failed", ex.getBindingResult().toString());
        return ResponseEntity.badRequest().body(errorResponse);
    }
}

// Error Response Class
@Data
public class ErrorResponse {
    private String message;
    private String details;
}

// Application Properties
@ConfigurationProperties(prefix = "example")
public class ExampleProperties {
    private String property;
}

// Code Creation Completed
```
