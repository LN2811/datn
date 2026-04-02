import { useEffect, useState } from "react";
import {
    ArrowRight,
    BookOpen,
    Brain,
    Briefcase,
    CheckCircle2,
    Clock3,
    FileText,
    FolderKanban,
} from 'lucide-react';
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import {api} from "@/api/axios.ts";
import { useParams } from "react-router-dom";

type Project = {
    id: string;
    name: string;
    description?: string;
};

export default function Project() {
    const navigate = useNavigate();
    const { user } = useAuth();
    const [projects, setProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isRefreshing, setIsRefreshing] = useState(false); 

    const {projectId} = useParams();
    useEffect(() => {
        let isMounted = true;
        const fetchProjects = async () => {
            if (!projectId) {
                if (!isMounted) return;
                setProjects([]);
                setLoading(false);
                return;
            }
            try{
                const response = await api.get(`/projects/${projectId}`);
                console.log(response.data);
                if(!isMounted) return;
                setProjects([response.data]);
                setLoading(false);
            } catch (err) {
                if (!isMounted) return;
                setError('khong thể tải dự án');
                setLoading(false);
            }
        };

        fetchProjects();

        return () => {
            isMounted = false;
        };
    }, [projectId]);

    return(
        <main className="main-project">
            <div className="project-header">
                {projects.map((project) => (
                    <div key={project.id}>
                        <h3>{project.name}</h3>
                        <p>{project.description}</p>
                    </div>
                ))}
                <h1>Dự án</h1>
            </div>
        </main>
    )
}
