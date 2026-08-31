import LoginPage from '@/components/pages/authentication/login';
import { SessionProvider } from '@/components/providers/SessionProvider';
import { Metadata } from 'next';

export const metadata: Metadata = { 
    title: "Login",
};

export default function Login(){
    return (
        <SessionProvider>
            <LoginPage />
        </SessionProvider>
    );
}