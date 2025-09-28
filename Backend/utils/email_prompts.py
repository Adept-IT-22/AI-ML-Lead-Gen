email_prompts = {
    "funding": {
        'generic': {
            'subject': 'Scaling After Funding?',
            'content': """
                <html>
                    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                        <p>Hello {first_name},</p>
                        
                        <p>Congrats to the <strong>{company_name}</strong> team on raising your <strong>{funding_round}</strong> round!</p>
                        
                        <p>We work with fast-growing AI/ML companies like yours to help scale operations by taking on core but time-consuming tasks such as <em>data annotation</em>. 
                        This lets your team stay focused on building while we handle the rest.</p>
                        
                        <p>Would you be open to a quick chat this week to explore how we can support <strong>{company_name}</strong>’s next phase of growth?</p>
                    </body>
                </html>
            """
        },
        'seed': {
            'subject': 'Build your MVP faster without stretching your team',
            'content': """
                <html>
                    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                        <p>Hello {first_name},</p>
                        
                        <p>Early stage founders often tell me the same thing: <em>"we know where we're going, we just dont have enough hands to get there fast enough."</em></p>
                        
                        <p>We plug the gap with skilled talent, working as an extension of your team. Its not outsourcing in the traditional sense; you get the extra hands you need to ship faster, without the cost and time of full-time hiring.</p>

                        <p>For one of our clients, its accelerated their development process, enabling them to rollout a new version of their AI-powered model ahead of schedule. Funding interest has followed ever since.</p>
                        
                        <p>Would you be open to a short chat next week to explore whether this kind of support could help accelerate your roadmap?</p>
                    </body>
                </html>
            """
        },
        'series': {
            'subject': 'Scale with Talent from Kenya',
            'content': """
                <html>
                    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                        <p>Hello {first_name},</p>
                        
                        <p>After a Series A or B round, growth comes with pressure: shipping faster, onboarding customers, and meeting investor expectations. And this comes with its challenges, especially if you can’t find the talent fast or affordably.</p>
                        
                        <p>We’re here to help by <b>augmenting existing teams with engineers and QA specialists who plug seamlessly into your Agile process</b>. You stay focused on strategy and innovation, while we handle the extra talent capacity you need to keep milestones on track.</p>
                        
                        <p>Would it make sense to explore how we could support your next growth sprint?</p>
                    </body>
                </html>
            """
        }
    },
    "hiring": {
        'subject': 'Help While You Scale',
        'content': """
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <p>Hi {first_name},</p>
                    
                    <p>I noticed <strong>{company_name}</strong> is expanding the team with roles in <strong>{hiring_area}</strong> — that’s exciting!</p>
                    
                    <p>As you grow, some tasks can start pulling focus from your core engineering/product roadmap. 
                    We specialize in supporting AI/ML companies with services like data annotation, customer engagement, and analytics — 
                    helping teams like yours move faster without the growing pains.</p>
                    
                    <p>Is it worth exploring how we could support <strong>{company_name}</strong> during this scaling phase?</p>
                </body>
            </html>
        """
    },
    "events": {
        'subject': 'Post-Event Connection',
        'content': """
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <p>Hi {first_name},</p>
                    
                    <p>I came across <strong>{company_name}</strong>’s participation in <strong>{event_name}</strong>.</p>
                    
                    <p>At Adept Technologies, we help AI/ML companies like <strong>{company_name}</strong> accelerate growth by providing 
                    <strong>scalable support services</strong> (data solutions, ML services, customer engagement).</p>
                    
                    <p>Would love to connect and share how we could complement what your team is doing.  
                    Would a 15-min call later this week work?</p>
                </body>
            </html>
        """
    }
}
